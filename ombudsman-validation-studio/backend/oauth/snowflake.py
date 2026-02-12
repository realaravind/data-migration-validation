"""
Snowflake OAuth Re-authentication Flow

Handles the complete OAuth flow for Snowflake when refresh tokens expire:
1. /authorize - Redirects user to Snowflake OAuth authorization page
2. /callback - Receives auth code, exchanges for tokens, saves to env
3. /status - Check OAuth configuration and token validity
"""

import os
import logging
import secrets
import subprocess
import asyncio
from typing import Optional
from urllib.parse import urlencode, quote
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from alerts.service import alert_service, AlertSeverity, AlertCategory

logger = logging.getLogger(__name__)
router = APIRouter()

# Store state tokens temporarily (in production, use Redis or database)
_oauth_states = {}


class OAuthStatus(BaseModel):
    """OAuth configuration status"""
    configured: bool
    has_client_id: bool
    has_client_secret: bool
    has_refresh_token: bool
    account: Optional[str]
    last_refresh: Optional[str] = None
    status: str  # 'valid', 'expired', 'not_configured', 'unknown'


class OAuthCallbackResult(BaseModel):
    """Result of OAuth callback"""
    success: bool
    message: str
    refresh_token_updated: bool = False


def _get_oauth_config():
    """Get OAuth configuration from environment"""
    return {
        "client_id": os.getenv("SNOWFLAKE_OAUTH_CLIENT_ID", ""),
        "client_secret": os.getenv("SNOWFLAKE_OAUTH_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("SNOWFLAKE_OAUTH_REFRESH_TOKEN", ""),
        "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
        "redirect_uri": os.getenv("SNOWFLAKE_OAUTH_REDIRECT_URI", ""),
    }


def _get_env_file_path() -> str:
    """Get the path to the environment file"""
    # Check common locations - must match where start-ombudsman.sh loads from
    possible_paths = [
        os.getenv("ENV_FILE_PATH"),
        "/ombudsman/ombudsman.env",  # Production: $BASE_DIR/ombudsman.env
        "/ombudsman/deploy/ombudsman.env",  # Fallback
        os.path.expanduser("~/.ombudsman.env"),
    ]

    for path in possible_paths:
        if path and os.path.exists(path):
            return path

    return possible_paths[1]  # Default to production path


def _update_env_file(key: str, value: str) -> bool:
    """
    Update a key in the environment file.

    Args:
        key: Environment variable name
        value: New value

    Returns:
        True if successful, False otherwise
    """
    env_path = _get_env_file_path()

    try:
        # Read existing content
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = []

        # Find and update the key, or add if not found
        key_found = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"export {key}="):
                # Replace the line
                if stripped.startswith("export "):
                    new_lines.append(f"export {key}={value}\n")
                else:
                    new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)

        # Add key if not found
        if not key_found:
            new_lines.append(f"{key}={value}\n")

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)

        # Also update current environment
        os.environ[key] = value

        logger.info(f"Updated {key} in {env_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to update env file: {e}")
        return False


@router.get("/status", response_model=OAuthStatus)
async def get_oauth_status():
    """Get current OAuth configuration status"""
    config = _get_oauth_config()

    configured = bool(config["client_id"] and config["account"])

    # Determine status
    if not configured:
        status = "not_configured"
    elif not config["refresh_token"]:
        status = "no_refresh_token"
    else:
        # Try to validate the refresh token by getting an access token
        try:
            await _exchange_refresh_token(config)
            status = "valid"
        except Exception as e:
            logger.warning(f"OAuth token validation failed: {e}")
            status = "expired"

    return OAuthStatus(
        configured=configured,
        has_client_id=bool(config["client_id"]),
        has_client_secret=bool(config["client_secret"]),
        has_refresh_token=bool(config["refresh_token"]),
        account=config["account"] if config["account"] else None,
        status=status
    )


@router.get("/authorize")
async def authorize(request: Request, redirect_after: Optional[str] = None):
    """
    Start OAuth authorization flow.
    Redirects user to Snowflake's OAuth authorization page.
    """
    config = _get_oauth_config()

    if not config["client_id"]:
        raise HTTPException(
            status_code=400,
            detail="SNOWFLAKE_OAUTH_CLIENT_ID not configured"
        )

    if not config["account"]:
        raise HTTPException(
            status_code=400,
            detail="SNOWFLAKE_ACCOUNT not configured"
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "created_at": datetime.utcnow().isoformat(),
        "redirect_after": redirect_after
    }

    # Build redirect URI - use configured or construct from request
    redirect_uri = config["redirect_uri"]
    if not redirect_uri:
        # Auto-construct from current request
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/oauth/snowflake/callback"

    # Build Snowflake authorization URL
    auth_params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    }

    auth_url = f"https://{config['account']}.snowflakecomputing.com/oauth/authorize?{urlencode(auth_params)}"

    logger.info(f"Redirecting to Snowflake OAuth: {auth_url}")

    return RedirectResponse(url=auth_url)


async def _exchange_refresh_token(config: dict) -> dict:
    """Exchange refresh token for access token (validation)"""
    token_url = f"https://{config['account']}.snowflakecomputing.com/oauth/token-request"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": config["refresh_token"],
            },
            auth=(config["client_id"], config["client_secret"]),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")

        return response.json()


async def _exchange_auth_code(config: dict, code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for tokens"""
    token_url = f"https://{config['account']}.snowflakecomputing.com/oauth/token-request"

    logger.info(f"Exchanging auth code at: {token_url}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(config["client_id"], config["client_secret"]),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0
        )

        logger.info(f"Token response status: {response.status_code}")

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"Token exchange failed: {error_detail}")
            raise Exception(f"Token exchange failed: {response.status_code} - {error_detail}")

        return response.json()


@router.get("/callback")
async def callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    OAuth callback handler.
    Receives authorization code from Snowflake, exchanges for tokens.
    """
    logger.info(f"OAuth callback received: code={'yes' if code else 'no'}, state={'yes' if state else 'no'}, error={error}")

    try:
        # Handle OAuth errors
        if error:
            logger.error(f"OAuth error: {error} - {error_description}")
            return HTMLResponse(content=f"""
            <html>
            <head><title>Snowflake OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1 style="color: #d32f2f;">Authentication Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_description or 'No details provided'}</p>
                <p><a href="javascript:window.close()">Close this window</a></p>
            </body>
            </html>
            """, status_code=400)

        # Validate state
        if not state or state not in _oauth_states:
            logger.error(f"Invalid or missing state parameter. Known states: {list(_oauth_states.keys())}")
            return HTMLResponse(content="""
            <html>
            <head><title>Snowflake OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1 style="color: #d32f2f;">Invalid Request</h1>
                <p>The authentication request has expired or is invalid. Please try again.</p>
                <p><a href="javascript:window.close()">Close this window</a></p>
            </body>
            </html>
            """, status_code=400)

        # Get and remove state data
        state_data = _oauth_states.pop(state, {})

        if not code:
            logger.error("No authorization code received")
            return HTMLResponse(content="""
            <html>
            <head><title>Snowflake OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1 style="color: #d32f2f;">No Authorization Code</h1>
                <p>No authorization code was received from Snowflake.</p>
                <p><a href="javascript:window.close()">Close this window</a></p>
            </body>
            </html>
            """, status_code=400)

        config = _get_oauth_config()

        # Build redirect URI (must match what was used in authorize)
        redirect_uri = config["redirect_uri"]
        if not redirect_uri:
            base_url = str(request.base_url).rstrip("/")
            redirect_uri = f"{base_url}/oauth/snowflake/callback"

        logger.info(f"Exchanging auth code, redirect_uri={redirect_uri}")
        # Exchange code for tokens
        tokens = await _exchange_auth_code(config, code, redirect_uri)

        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        if not refresh_token:
            logger.error("No refresh token in response")
            return HTMLResponse(content="""
            <html>
            <head><title>Snowflake OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1 style="color: #d32f2f;">No Refresh Token</h1>
                <p>Snowflake did not return a refresh token. This may be due to your security integration settings.</p>
                <p>Ensure OAUTH_ISSUE_REFRESH_TOKENS = TRUE in your security integration.</p>
                <p><a href="javascript:window.close()">Close this window</a></p>
            </body>
            </html>
            """, status_code=400)

        # Save the new refresh token to env file
        if _update_env_file("SNOWFLAKE_OAUTH_REFRESH_TOKEN", refresh_token):
            logger.info("Successfully updated refresh token in env file")

            # Clear any existing OAuth error alerts
            # (This could be enhanced to specifically remove OAuth alerts)

            # Add success alert
            alert_service.add_alert(
                message="Snowflake OAuth token has been refreshed successfully. Connection should now work.",
                source="oauth/snowflake",
                severity=AlertSeverity.INFO,
                category=AlertCategory.AUTHENTICATION,
                title="Snowflake Re-authenticated"
            )

            return HTMLResponse(content="""
            <html>
            <head>
                <title>Snowflake OAuth Success</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    .success { color: #2e7d32; }
                    .checkmark { font-size: 64px; color: #2e7d32; }
                    .spinner { width: 30px; height: 30px; border: 4px solid #f3f3f3; border-top: 4px solid #1976d2; border-radius: 50%; animation: spin 1s linear infinite; display: inline-block; margin-left: 10px; vertical-align: middle; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    .btn { background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 20px; border: none; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class="checkmark">&#10004;</div>
                <h1 class="success">Authentication Successful!</h1>
                <p>Your Snowflake OAuth token has been refreshed and saved.</p>
                <p id="status">Encrypting secrets and restarting server... <span class="spinner"></span></p>
                <button id="closeBtn" class="btn" style="display:none" onclick="window.close()">Close Window</button>
                <script>
                    // Notify parent window if opened as popup
                    if (window.opener) {
                        window.opener.postMessage({ type: 'snowflake_oauth_success' }, '*');
                    }

                    // Auto-trigger finalization
                    async function finalize() {
                        try {
                            const response = await fetch(window.location.origin + '/oauth/snowflake/finalize', {
                                method: 'POST'
                            });
                            const data = await response.json();

                            document.getElementById('status').innerHTML = '✓ ' + data.message + '<br><br>You can close this window now.';
                            document.getElementById('closeBtn').style.display = 'inline-block';

                            // Notify parent about finalization
                            if (window.opener) {
                                window.opener.postMessage({ type: 'snowflake_oauth_finalized' }, '*');
                            }

                            // Auto-close after 8 seconds
                            setTimeout(() => window.close(), 8000);
                        } catch (error) {
                            document.getElementById('status').innerHTML =
                                'Token saved but auto-restart failed.<br>' +
                                'Please run: <code>sudo ./start-ombudsman.sh encrypt-secrets && sudo ./start-ombudsman.sh restart</code>';
                            document.getElementById('closeBtn').style.display = 'inline-block';
                        }
                    }

                    // Start finalization after a short delay
                    setTimeout(finalize, 1000);
                </script>
            </body>
            </html>
            """)
        else:
            logger.error("Failed to save refresh token to env file")
            return HTMLResponse(content=f"""
            <html>
            <head><title>Snowflake OAuth Warning</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1 style="color: #ed6c02;">Token Received - Manual Update Required</h1>
                <p>Authentication was successful, but the token could not be automatically saved.</p>
                <p>Please manually update your environment file with:</p>
                <pre style="background: #f5f5f5; padding: 15px; overflow-x: auto; border-radius: 4px;">SNOWFLAKE_OAUTH_REFRESH_TOKEN={refresh_token}</pre>
                <p>Then restart the backend service.</p>
                <p><a href="javascript:window.close()">Close this window</a></p>
            </body>
            </html>
            """)

    except Exception as e:
        logger.exception(f"Token exchange failed: {e}")
        return HTMLResponse(content=f"""
        <html>
        <head><title>Snowflake OAuth Error</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d32f2f;">Token Exchange Failed</h1>
            <p>{str(e)}</p>
            <p>Please check your OAuth client configuration in Snowflake.</p>
            <p><a href="javascript:window.close()">Close this window</a></p>
        </body>
        </html>
        """, status_code=500)


@router.get("/test")
async def test_connection():
    """Test current OAuth connection"""
    config = _get_oauth_config()

    if not config["refresh_token"]:
        return {
            "status": "error",
            "message": "No refresh token configured",
            "action_required": "authenticate"
        }

    try:
        tokens = await _exchange_refresh_token(config)
        return {
            "status": "success",
            "message": "OAuth token is valid",
            "token_type": tokens.get("token_type"),
            "expires_in": tokens.get("expires_in")
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "action_required": "re-authenticate"
        }


def _get_start_script_path() -> str:
    """Get the path to start-ombudsman.sh"""
    possible_paths = [
        "/ombudsman/deploy/start-ombudsman.sh",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "deploy", "start-ombudsman.sh"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return possible_paths[0]


def _run_encrypt_and_restart():
    """Run encrypt-secrets and then restart the server (runs in background)"""
    import time
    script_path = _get_start_script_path()
    base_dir = os.path.dirname(os.path.dirname(script_path))

    try:
        # Run encrypt-secrets
        logger.info(f"Running encrypt-secrets from {script_path}")
        result = subprocess.run(
            ["sudo", script_path, "encrypt-secrets"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            logger.error(f"encrypt-secrets failed: {result.stderr}")
            return False
        logger.info("encrypt-secrets completed successfully")

        # Small delay before restart
        time.sleep(2)

        # Trigger restart (this will kill the current process)
        logger.info("Triggering server restart...")
        subprocess.Popen(
            ["sudo", script_path, "restart"],
            cwd=base_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent process
        )
        return True

    except Exception as e:
        logger.exception(f"Failed to encrypt and restart: {e}")
        return False


@router.post("/finalize")
async def finalize_oauth(background_tasks: BackgroundTasks):
    """
    Finalize OAuth by encrypting secrets and restarting the server.
    Call this after OAuth callback completes successfully.
    """
    logger.info("OAuth finalize requested - will encrypt secrets and restart")

    # Add the encrypt and restart to background tasks
    # We use a thread to avoid blocking
    import threading

    def delayed_restart():
        import time
        time.sleep(3)  # Give time for response to be sent
        _run_encrypt_and_restart()

    thread = threading.Thread(target=delayed_restart, daemon=True)
    thread.start()

    return JSONResponse(content={
        "status": "success",
        "message": "Secrets will be encrypted and server will restart in ~5 seconds"
    })


@router.get("/finalize-page")
async def finalize_page():
    """
    Page shown after OAuth success to trigger encrypt and restart.
    """
    return HTMLResponse(content="""
    <html>
    <head>
        <title>Finalizing Snowflake OAuth</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
            .spinner { width: 50px; height: 50px; border: 5px solid #f3f3f3; border-top: 5px solid #1976d2; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .success { color: #2e7d32; }
            .error { color: #d32f2f; }
            .btn { background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 20px; border: none; cursor: pointer; font-size: 16px; }
            .btn:disabled { background: #ccc; cursor: not-allowed; }
            #status { margin: 20px 0; padding: 15px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>Finalizing Authentication</h1>
        <div id="spinner" class="spinner"></div>
        <div id="status">Encrypting secrets and restarting server...</div>
        <button id="closeBtn" class="btn" style="display:none" onclick="window.close()">Close Window</button>

        <script>
            const API_BASE = window.location.origin;

            async function finalize() {
                try {
                    const response = await fetch(API_BASE + '/oauth/snowflake/finalize', {
                        method: 'POST'
                    });
                    const data = await response.json();

                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('status').innerHTML = `
                        <div class="success">
                            <h2>✓ Success!</h2>
                            <p>${data.message}</p>
                            <p>The server is restarting. Please wait a moment, then refresh the main application.</p>
                        </div>
                    `;
                    document.getElementById('closeBtn').style.display = 'inline-block';

                    // Notify parent window
                    if (window.opener) {
                        window.opener.postMessage({ type: 'snowflake_oauth_finalized' }, '*');
                    }

                    // Auto-close after 10 seconds
                    setTimeout(() => window.close(), 10000);

                } catch (error) {
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('status').innerHTML = `
                        <div class="error">
                            <h2>Error</h2>
                            <p>Failed to finalize: ${error.message}</p>
                            <p>You may need to manually run: sudo ./start-ombudsman.sh encrypt-secrets && sudo ./start-ombudsman.sh restart</p>
                        </div>
                    `;
                    document.getElementById('closeBtn').style.display = 'inline-block';
                }
            }

            // Start finalization immediately
            finalize();
        </script>
    </body>
    </html>
    """)
