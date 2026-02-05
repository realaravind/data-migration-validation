#!/bin/bash
#
# Ombudsman Validation Studio - Startup Script
# Usage: ./start-ombudsman.sh [start|stop|status]
#        OMBUDSMAN_BASE_DIR=/custom/path ./start-ombudsman.sh start
#

# ==============================================
# Auto-detect base directory from script location
# ==============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# BASE_DIR is parent of deploy/ directory, can be overridden
if [ -n "$OMBUDSMAN_BASE_DIR" ]; then
    BASE_DIR="$OMBUDSMAN_BASE_DIR"
else
    BASE_DIR="$(dirname "$SCRIPT_DIR")"
fi

# ==============================================
# SOPS Encryption Support
# ==============================================
SOPS_KEY_FILE="${SOPS_AGE_KEY_FILE:-$BASE_DIR/.sops-age-key.txt}"
SOPS_CONFIG="$BASE_DIR/.sops.yaml"
ENV_FILE_ENC="${OMBUDSMAN_ENV_FILE:-$BASE_DIR/ombudsman.env}.enc"

# Check if SOPS is available
has_sops() {
    command -v sops &> /dev/null
}

# Check if age is available
has_age() {
    command -v age &> /dev/null
}

# Check if file is SOPS-encrypted
is_sops_encrypted() {
    local file="$1"
    [ -f "$file" ] && head -1 "$file" 2>/dev/null | grep -q "^sops_"
}

# Decrypt SOPS file to stdout
decrypt_sops_env() {
    local encrypted_file="$1"

    if [ ! -f "$SOPS_KEY_FILE" ]; then
        echo "ERROR: SOPS key file not found at $SOPS_KEY_FILE" >&2
        echo "Run './start-ombudsman.sh init-secrets' to generate a key." >&2
        return 1
    fi

    SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --decrypt "$encrypted_file"
}

# ==============================================
# Load Environment File
# ==============================================
ENV_FILE="${OMBUDSMAN_ENV_FILE:-$BASE_DIR/ombudsman.env}"
TEMPLATE_FILE="$SCRIPT_DIR/ombudsman.env"

# Determine which env file to use
load_env_file() {
    # Priority: encrypted file (if valid) > plaintext file > template
    if [ -f "$ENV_FILE_ENC" ] && has_sops && is_sops_encrypted "$ENV_FILE_ENC"; then
        echo "Loading encrypted config from: $ENV_FILE_ENC"
        local decrypted
        decrypted=$(decrypt_sops_env "$ENV_FILE_ENC") || exit 1
        set -a
        eval "$decrypted"
        set +a
    elif [ -f "$ENV_FILE_ENC" ] && ! is_sops_encrypted "$ENV_FILE_ENC"; then
        echo ""
        echo "=========================================="
        echo "WARNING: Invalid encrypted config file"
        echo "=========================================="
        echo ""
        echo "$ENV_FILE_ENC exists but is not properly encrypted."
        echo "(It may contain plaintext from a failed encryption attempt)"
        echo ""

        # Check if plaintext file exists as fallback
        if [ -f "$ENV_FILE" ]; then
            echo "Found plaintext config at $ENV_FILE"
            echo "Loading config from: $ENV_FILE"
            set -a
            source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
            set +a
            echo ""
            echo "To fix: rm $ENV_FILE_ENC && ./start-ombudsman.sh encrypt-secrets"
        else
            echo "No plaintext config found either."
            echo ""
            echo "Options to recover:"
            echo "  1. Re-run installer:  sudo ./install-ombudsman.sh"
            echo "  2. Copy template and edit manually:"
            echo "     cp $TEMPLATE_FILE $ENV_FILE"
            echo "     nano $ENV_FILE"
            echo "     rm $ENV_FILE_ENC"
            echo ""

            # Offer to copy template now
            if [ -f "$TEMPLATE_FILE" ]; then
                read -p "Copy template now and edit? (Y/n): " copy_choice
                copy_choice="${copy_choice:-Y}"
                if [ "$copy_choice" = "Y" ] || [ "$copy_choice" = "y" ]; then
                    cp "$TEMPLATE_FILE" "$ENV_FILE"
                    echo ""
                    echo "Template copied to $ENV_FILE"
                    echo "Edit with: nano $ENV_FILE"
                    echo "Then remove invalid .enc: rm $ENV_FILE_ENC"
                    echo "Then restart: ./start-ombudsman.sh start"
                fi
            fi
            exit 1
        fi
    elif [ -f "$ENV_FILE" ]; then
        echo "Loading config from: $ENV_FILE"
        set -a
        source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
        set +a
    elif [ -f "$TEMPLATE_FILE" ]; then
        echo "Config file not found at $ENV_FILE"
        echo "Copying template from $TEMPLATE_FILE..."
        cp "$TEMPLATE_FILE" "$ENV_FILE"
        echo ""
        echo "=========================================="
        echo "IMPORTANT: Edit your config file!"
        echo "=========================================="
        echo "Run: nano $ENV_FILE"
        echo "Update your database credentials, then run this script again."
        echo ""
        echo "To encrypt secrets after editing:"
        echo "  ./start-ombudsman.sh encrypt-secrets"
        echo "=========================================="
        echo ""
        exit 1
    else
        echo "Error: Template file not found at $TEMPLATE_FILE"
        exit 1
    fi
}

# Load environment (skip for certain commands that don't need it)
case "${1:-start}" in
    init-secrets|encrypt-secrets|decrypt-secrets|edit-secrets|help)
        # These commands handle env loading themselves
        ;;
    *)
        load_env_file
        ;;
esac

# ==============================================
# Configuration - Derived from BASE_DIR
# ==============================================
# BASE_DIR is already set at script start (auto-detected or from OMBUDSMAN_BASE_DIR)
BACKEND_DIR="$BASE_DIR/ombudsman-validation-studio/backend"
FRONTEND_DIR="$BASE_DIR/ombudsman-validation-studio/frontend"
CORE_DIR="$BASE_DIR/ombudsman_core/src"
DATA_DIR="${OMBUDSMAN_DATA_DIR:-$BASE_DIR/data}"
LOG_DIR="${OMBUDSMAN_LOG_DIR:-$BASE_DIR/logs}"

# Server settings
BACKEND_HOST="0.0.0.0"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="0.0.0.0"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# ==============================================
# Environment Variables for Python
# ==============================================
export OMBUDSMAN_DATA_DIR="$DATA_DIR"
export OMBUDSMAN_CORE_DIR="${OMBUDSMAN_CORE_DIR:-$CORE_DIR/ombudsman/config}"
export OMBUDSMAN_LOG_DIR="$LOG_DIR"
export PYTHONPATH="$BACKEND_DIR:$CORE_DIR"

# Build SQL Server connection string from individual vars
export SQLSERVER_CONN_STR="DRIVER={ODBC Driver 18 for SQL Server};SERVER=${MSSQL_HOST},${MSSQL_PORT};DATABASE=${MSSQL_DATABASE};UID=${MSSQL_USER};PWD=${MSSQL_PASSWORD};TrustServerCertificate=yes;"

# ==============================================
# Functions
# ==============================================

kill_process_on_port() {
    local port=$1
    local pids=$(lsof -t -i:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "Killing processes on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

create_directories() {
    echo "Creating directories..."
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR/projects"
    mkdir -p "$DATA_DIR/pipelines"
    mkdir -p "$DATA_DIR/results"
    mkdir -p "$DATA_DIR/batch_jobs"
    mkdir -p "$DATA_DIR/workloads"
    mkdir -p "$DATA_DIR/auth"
}

start_backend() {
    echo "Starting backend..."

    # Kill any existing process on the backend port
    kill_process_on_port "$BACKEND_PORT"

    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping existing backend (PID: $PID)"
            kill $PID 2>/dev/null
            sleep 2
        fi
        rm -f "$LOG_DIR/backend.pid"
    fi

    cd "$BACKEND_DIR"

    # Export all environment variables for the backend process
    nohup env \
        OMBUDSMAN_DATA_DIR="$OMBUDSMAN_DATA_DIR" \
        OMBUDSMAN_CORE_DIR="$OMBUDSMAN_CORE_DIR" \
        OMBUDSMAN_LOG_DIR="$OMBUDSMAN_LOG_DIR" \
        PYTHONPATH="$PYTHONPATH" \
        AUTH_BACKEND="${AUTH_BACKEND:-sqlite}" \
        AUTH_DB_SERVER="${AUTH_DB_SERVER:-}" \
        AUTH_DB_NAME="${AUTH_DB_NAME:-}" \
        AUTH_DB_USER="${AUTH_DB_USER:-}" \
        AUTH_DB_PASSWORD="${AUTH_DB_PASSWORD:-}" \
        MSSQL_HOST="${MSSQL_HOST:-}" \
        MSSQL_PORT="${MSSQL_PORT:-1433}" \
        MSSQL_USER="${MSSQL_USER:-}" \
        MSSQL_PASSWORD="${MSSQL_PASSWORD:-}" \
        MSSQL_DATABASE="${MSSQL_DATABASE:-}" \
        SQLSERVER_CONN_STR="$SQLSERVER_CONN_STR" \
        SNOWFLAKE_USER="${SNOWFLAKE_USER:-}" \
        SNOWFLAKE_PASSWORD="${SNOWFLAKE_PASSWORD:-}" \
        SNOWFLAKE_TOKEN="${SNOWFLAKE_TOKEN:-}" \
        SNOWFLAKE_ACCOUNT="${SNOWFLAKE_ACCOUNT:-}" \
        SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-}" \
        SNOWFLAKE_ROLE="${SNOWFLAKE_ROLE:-}" \
        SNOWFLAKE_DATABASE="${SNOWFLAKE_DATABASE:-}" \
        SNOWFLAKE_SCHEMA="${SNOWFLAKE_SCHEMA:-}" \
        SECRET_KEY="${SECRET_KEY:-change-me}" \
        CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}" \
        LLM_PROVIDER="${LLM_PROVIDER:-ollama}" \
        LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.1}" \
        LLM_MAX_TOKENS="${LLM_MAX_TOKENS:-2048}" \
        LLM_TIMEOUT="${LLM_TIMEOUT:-30}" \
        OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}" \
        OLLAMA_MODEL="${OLLAMA_MODEL:-llama2}" \
        OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o-mini}" \
        AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}" \
        AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}" \
        AZURE_OPENAI_DEPLOYMENT="${AZURE_OPENAI_DEPLOYMENT:-}" \
        AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2024-02-15-preview}" \
        ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
        ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-3-5-sonnet-20241022}" \
        ./venv/bin/python -m uvicorn main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        --log-level info \
        > "$LOG_DIR/backend.log" 2>&1 &

    echo $! > "$LOG_DIR/backend.pid"
    echo "Backend started (PID: $!)"
    echo "Backend log: $LOG_DIR/backend.log"
}

start_frontend() {
    echo "Starting frontend..."

    # Kill any existing process on the frontend port
    kill_process_on_port "$FRONTEND_PORT"

    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping existing frontend (PID: $PID)"
            kill $PID 2>/dev/null
            sleep 2
        fi
        rm -f "$LOG_DIR/frontend.pid"
    fi

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi

    # Build if dist doesn't exist
    if [ ! -d "dist" ]; then
        echo "Building frontend..."
        npm run build
    fi

    nohup npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort \
        > "$LOG_DIR/frontend.log" 2>&1 &

    echo $! > "$LOG_DIR/frontend.pid"
    echo "Frontend started (PID: $!)"
    echo "Frontend log: $LOG_DIR/frontend.log"
}

stop_backend() {
    echo "Stopping backend..."
    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo "Backend stopped (PID: $PID)"
        else
            echo "Backend not running"
        fi
        rm -f "$LOG_DIR/backend.pid"
    else
        echo "No backend PID file found"
    fi
    # Also kill any orphaned processes on the port
    kill_process_on_port "$BACKEND_PORT"
}

stop_frontend() {
    echo "Stopping frontend..."
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo "Frontend stopped (PID: $PID)"
        else
            echo "Frontend not running"
        fi
        rm -f "$LOG_DIR/frontend.pid"
    else
        echo "No frontend PID file found"
    fi
    # Also kill any orphaned processes on the port
    kill_process_on_port "$FRONTEND_PORT"
}

status() {
    echo "=== Ombudsman Status ==="
    echo ""

    echo "Backend:"
    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "  Running (PID: $PID)"
            echo "  URL: http://$BACKEND_HOST:$BACKEND_PORT"
        else
            echo "  Not running (stale PID file)"
        fi
    else
        echo "  Not running"
    fi

    echo ""
    echo "Frontend:"
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "  Running (PID: $PID)"
            echo "  URL: http://$FRONTEND_HOST:$FRONTEND_PORT"
        else
            echo "  Not running (stale PID file)"
        fi
    else
        echo "  Not running"
    fi

    echo ""
    echo "Environment:"
    echo "  OMBUDSMAN_DATA_DIR: $OMBUDSMAN_DATA_DIR"
    echo "  OMBUDSMAN_CORE_DIR: $OMBUDSMAN_CORE_DIR"
    echo "  OMBUDSMAN_LOG_DIR: $OMBUDSMAN_LOG_DIR"
}

show_logs() {
    echo "=== Recent Backend Logs ==="
    if [ -f "$LOG_DIR/backend.log" ]; then
        tail -20 "$LOG_DIR/backend.log"
    else
        echo "No backend log found"
    fi

    echo ""
    echo "=== Recent Frontend Logs ==="
    if [ -f "$LOG_DIR/frontend.log" ]; then
        tail -20 "$LOG_DIR/frontend.log"
    else
        echo "No frontend log found"
    fi
}

# ==============================================
# Main
# ==============================================

setup_auth() {
    echo "Setting up authentication database..."

    if [ "${AUTH_BACKEND:-sqlite}" = "sqlserver" ]; then
        if [ -n "$AUTH_DB_SERVER" ] && [ -n "$AUTH_DB_USER" ] && [ -n "$AUTH_DB_PASSWORD" ]; then
            cd "$BACKEND_DIR"

            echo "Creating auth tables in SQL Server..."
            AUTH_DB_SERVER="$AUTH_DB_SERVER" \
            AUTH_DB_NAME="${AUTH_DB_NAME:-ovs_studio}" \
            AUTH_DB_USER="$AUTH_DB_USER" \
            AUTH_DB_PASSWORD="$AUTH_DB_PASSWORD" \
            ./venv/bin/python auth/setup_sql_server_auth.py

            echo "Creating default admin user..."
            AUTH_DB_SERVER="$AUTH_DB_SERVER" \
            AUTH_DB_NAME="${AUTH_DB_NAME:-ovs_studio}" \
            AUTH_DB_USER="$AUTH_DB_USER" \
            AUTH_DB_PASSWORD="$AUTH_DB_PASSWORD" \
            ./venv/bin/python -c "
from auth.sqlserver_auth_repository import SQLServerAuthRepository
from auth.models import UserCreate, UserRole
repo = SQLServerAuthRepository()
try:
    user = UserCreate(username='admin', email='admin@localhost', password='admin123', role=UserRole.ADMIN)
    repo.create_user(user)
    print('Default admin user created (admin/admin123)')
except ValueError as e:
    print('Admin user already exists')
except Exception as e:
    print(f'Could not create admin user: {e}')
"
            echo "Auth setup complete!"
        else
            echo "ERROR: AUTH_BACKEND=sqlserver but credentials not set in $ENV_FILE"
            exit 1
        fi
    else
        echo "Using SQLite for authentication. No setup needed."
    fi
}

case "${1:-start}" in
    start)
        create_directories
        start_backend
        sleep 2  # Wait for backend to initialize
        start_frontend
        echo ""
        echo "=== Ombudsman Started ==="
        echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
        echo "Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
        echo ""
        echo "Use './start-ombudsman.sh status' to check status"
        echo "Use './start-ombudsman.sh logs' to view logs"
        echo "Use './start-ombudsman.sh stop' to stop services"
        ;;
    stop)
        stop_frontend
        stop_backend
        ;;
    restart)
        stop_frontend
        stop_backend
        sleep 2
        create_directories
        start_backend
        sleep 2
        start_frontend
        ;;
    status)
        status
        ;;
    logs)
        show_logs
        ;;
    backend)
        create_directories
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    setup-auth)
        setup_auth
        ;;
    rebuild-frontend)
        echo "Rebuilding frontend with API URL: ${VITE_API_URL:-http://localhost:8000}"
        cd "$FRONTEND_DIR"
        echo "VITE_API_URL=${VITE_API_URL:-http://localhost:8000}" > .env
        npm run build
        echo "Frontend rebuilt. Restart frontend to apply changes."
        ;;
    enable-service)
        echo "Installing systemd services for auto-start on boot..."

        if [ "$EUID" -ne 0 ]; then
            echo "ERROR: This command requires root privileges. Run with sudo."
            exit 1
        fi

        # Create log directory if not exists
        mkdir -p "$LOG_DIR"

        # Copy service files
        cp "$SCRIPT_DIR/systemd/ombudsman-backend.service" /etc/systemd/system/
        cp "$SCRIPT_DIR/systemd/ombudsman-frontend.service" /etc/systemd/system/

        # Reload systemd
        systemctl daemon-reload

        # Enable services
        systemctl enable ombudsman-backend
        systemctl enable ombudsman-frontend

        echo ""
        echo "Systemd services installed and enabled!"
        echo ""
        echo "Commands:"
        echo "  sudo systemctl start ombudsman-backend    # Start backend"
        echo "  sudo systemctl start ombudsman-frontend   # Start frontend"
        echo "  sudo systemctl stop ombudsman-backend     # Stop backend"
        echo "  sudo systemctl stop ombudsman-frontend    # Stop frontend"
        echo "  sudo systemctl status ombudsman-backend   # Check backend status"
        echo "  sudo systemctl status ombudsman-frontend  # Check frontend status"
        echo ""
        echo "Services will auto-start on boot."
        echo "To start now: sudo systemctl start ombudsman-backend ombudsman-frontend"
        ;;
    disable-service)
        echo "Disabling systemd services..."

        if [ "$EUID" -ne 0 ]; then
            echo "ERROR: This command requires root privileges. Run with sudo."
            exit 1
        fi

        systemctl stop ombudsman-frontend 2>/dev/null || true
        systemctl stop ombudsman-backend 2>/dev/null || true
        systemctl disable ombudsman-frontend 2>/dev/null || true
        systemctl disable ombudsman-backend 2>/dev/null || true

        echo "Systemd services disabled. They will not auto-start on boot."
        ;;
    update)
        echo "=========================================="
        echo "Updating Ombudsman Validation Studio..."
        echo "=========================================="

        # Stop services first
        echo ""
        echo "[1/6] Stopping services..."
        systemctl stop ombudsman-frontend 2>/dev/null || true
        systemctl stop ombudsman-backend 2>/dev/null || true

        # Pull latest code
        echo ""
        echo "[2/6] Pulling latest code..."
        cd "$BASE_DIR"
        git pull

        # Update Python dependencies
        echo ""
        echo "[3/6] Updating Python dependencies..."
        cd "$BACKEND_DIR"
        ./venv/bin/pip install --upgrade pip
        ./venv/bin/pip install -r requirements.txt

        # Update frontend dependencies
        echo ""
        echo "[4/6] Updating frontend dependencies..."
        cd "$FRONTEND_DIR"
        npm install

        # Fix any vulnerabilities
        echo ""
        echo "[5/6] Fixing vulnerabilities..."
        npm audit fix 2>/dev/null || true

        # Rebuild frontend
        echo ""
        echo "[6/6] Rebuilding frontend..."
        npm run build

        # Restart services
        echo ""
        echo "Restarting services..."
        systemctl start ombudsman-backend
        sleep 2
        systemctl start ombudsman-frontend

        echo ""
        echo "=========================================="
        echo "Update complete!"
        echo "=========================================="
        echo ""
        echo "Check status: sudo systemctl status ombudsman-backend"
        ;;
    init-secrets)
        echo "=========================================="
        echo "Initializing SOPS encryption..."
        echo "=========================================="

        # Check dependencies
        if ! has_sops; then
            echo "ERROR: SOPS is not installed."
            echo "Install with: sudo apt-get install -y sops"
            echo "Or download from: https://github.com/getsops/sops/releases"
            exit 1
        fi

        if ! has_age; then
            echo "ERROR: age is not installed."
            echo "Install with: sudo apt-get install -y age"
            echo "Or download from: https://github.com/FiloSottile/age/releases"
            exit 1
        fi

        # Generate age key if not exists
        if [ -f "$SOPS_KEY_FILE" ]; then
            echo "Age key already exists at: $SOPS_KEY_FILE"
            AGE_PUBLIC_KEY=$(grep "public key:" "$SOPS_KEY_FILE" | cut -d: -f2 | tr -d ' ')
        else
            echo "Generating new age encryption key..."
            mkdir -p "$(dirname "$SOPS_KEY_FILE")"
            age-keygen -o "$SOPS_KEY_FILE" 2>&1 | tee /tmp/age-keygen-output.txt
            chmod 600 "$SOPS_KEY_FILE"
            AGE_PUBLIC_KEY=$(grep "public key:" /tmp/age-keygen-output.txt | cut -d: -f2 | tr -d ' ')
            rm -f /tmp/age-keygen-output.txt
            echo ""
            echo "Age key generated at: $SOPS_KEY_FILE"
        fi

        # Create .sops.yaml config
        SOPS_CONFIG="$BASE_DIR/.sops.yaml"
        cat > "$SOPS_CONFIG" << EOF
creation_rules:
  # Match .env files for encryption
  - path_regex: .*\.env$
    age: $AGE_PUBLIC_KEY
  # Match .env.enc files for decryption
  - path_regex: .*\.env\.enc$
    age: $AGE_PUBLIC_KEY
EOF
        echo "SOPS config created at: $SOPS_CONFIG"

        echo ""
        echo "=========================================="
        echo "SOPS initialization complete!"
        echo "=========================================="
        echo ""
        echo "Your encryption key is stored at:"
        echo "  $SOPS_KEY_FILE"
        echo ""
        echo "IMPORTANT: Back up this key securely!"
        echo "Without it, you cannot decrypt your secrets."
        echo ""
        echo "Next steps:"
        echo "  1. Edit your config: nano $ENV_FILE"
        echo "  2. Encrypt it:       ./start-ombudsman.sh encrypt-secrets"
        echo ""
        ;;
    encrypt-secrets)
        echo "=========================================="
        echo "Encrypting secrets..."
        echo "=========================================="

        if ! has_sops; then
            echo "ERROR: SOPS is not installed. Run './start-ombudsman.sh init-secrets' first."
            exit 1
        fi

        if [ ! -f "$SOPS_KEY_FILE" ]; then
            echo "ERROR: No encryption key found. Run './start-ombudsman.sh init-secrets' first."
            exit 1
        fi

        if [ ! -f "$ENV_FILE" ]; then
            echo "ERROR: Config file not found at $ENV_FILE"
            exit 1
        fi

        # Encrypt the env file
        echo "Encrypting $ENV_FILE..."
        SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --encrypt "$ENV_FILE" > "$ENV_FILE_ENC"

        echo ""
        echo "=========================================="
        echo "Encryption complete!"
        echo "=========================================="
        echo ""
        echo "Encrypted file: $ENV_FILE_ENC"
        echo ""
        echo "You can now safely delete the plaintext file:"
        echo "  rm $ENV_FILE"
        echo ""
        echo "The services will automatically use the encrypted file."
        echo ""
        ;;
    decrypt-secrets)
        echo "=========================================="
        echo "Decrypting secrets..."
        echo "=========================================="

        if ! has_sops; then
            echo "ERROR: SOPS is not installed."
            exit 1
        fi

        if [ ! -f "$SOPS_KEY_FILE" ]; then
            echo "ERROR: No decryption key found at $SOPS_KEY_FILE"
            exit 1
        fi

        if [ ! -f "$ENV_FILE_ENC" ]; then
            echo "ERROR: Encrypted file not found at $ENV_FILE_ENC"
            exit 1
        fi

        if [ -f "$ENV_FILE" ]; then
            echo "WARNING: Plaintext file already exists at $ENV_FILE"
            read -p "Overwrite? (y/N): " confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                echo "Aborted."
                exit 0
            fi
        fi

        # Decrypt
        echo "Decrypting $ENV_FILE_ENC..."
        SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --decrypt "$ENV_FILE_ENC" > "$ENV_FILE"
        chmod 600 "$ENV_FILE"

        echo ""
        echo "Decrypted to: $ENV_FILE"
        echo ""
        echo "SECURITY WARNING: The plaintext file contains secrets!"
        echo "Remember to re-encrypt after editing:"
        echo "  ./start-ombudsman.sh encrypt-secrets"
        echo ""
        ;;
    edit-secrets)
        echo "=========================================="
        echo "Editing encrypted secrets..."
        echo "=========================================="

        if ! has_sops; then
            echo "ERROR: SOPS is not installed."
            exit 1
        fi

        if [ ! -f "$SOPS_KEY_FILE" ]; then
            echo "ERROR: No decryption key found at $SOPS_KEY_FILE"
            exit 1
        fi

        # Determine which file to edit
        if [ -f "$ENV_FILE_ENC" ]; then
            echo "Opening encrypted file for editing..."
            echo "(File will be decrypted, edited, then re-encrypted automatically)"
            echo ""
            SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" "$ENV_FILE_ENC"
            echo ""
            echo "Changes saved and encrypted."
        elif [ -f "$ENV_FILE" ]; then
            echo "No encrypted file found. Opening plaintext file..."
            ${EDITOR:-nano} "$ENV_FILE"
            echo ""
            echo "To encrypt your secrets, run:"
            echo "  ./start-ombudsman.sh encrypt-secrets"
        else
            echo "ERROR: No config file found."
            echo "Run the start script first to create a config from template."
            exit 1
        fi
        ;;
    help)
        echo "Ombudsman Validation Studio - Command Reference"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Service Commands:"
        echo "  start              Start backend and frontend services"
        echo "  stop               Stop all services"
        echo "  restart            Restart all services"
        echo "  status             Show service status"
        echo "  logs               Show recent logs"
        echo "  backend            Start only the backend"
        echo "  frontend           Start only the frontend"
        echo ""
        echo "Setup Commands:"
        echo "  setup-auth         Initialize authentication database"
        echo "  rebuild-frontend   Rebuild frontend (after config changes)"
        echo "  enable-service     Install systemd services (auto-start on boot)"
        echo "  disable-service    Remove systemd services"
        echo "  update             Update to latest version (git pull + rebuild)"
        echo ""
        echo "Secrets Management (SOPS):"
        echo "  init-secrets       Initialize SOPS encryption (generates age key)"
        echo "  encrypt-secrets    Encrypt the config file"
        echo "  decrypt-secrets    Decrypt to plaintext (for backup/migration)"
        echo "  edit-secrets       Edit encrypted config (auto decrypt/encrypt)"
        echo ""
        echo "Environment Variables:"
        echo "  OMBUDSMAN_BASE_DIR   Base directory (default: auto-detected from script location)"
        echo "  OMBUDSMAN_ENV_FILE   Path to config file (default: \$BASE_DIR/ombudsman.env)"
        echo "  SOPS_AGE_KEY_FILE    Path to age key (default: \$BASE_DIR/.sops-age-key.txt)"
        echo ""
        echo "Current BASE_DIR: $BASE_DIR"
        echo ""
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|backend|frontend|setup-auth|rebuild-frontend|enable-service|disable-service|update|init-secrets|encrypt-secrets|decrypt-secrets|edit-secrets|help}"
        exit 1
        ;;
esac
