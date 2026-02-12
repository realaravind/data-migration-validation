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

# Check if file is SOPS-encrypted (has ENC[ markers or sops_ metadata)
is_sops_encrypted() {
    local file="$1"
    [ -f "$file" ] || return 1

    # Check for SOPS encryption markers (ENC[ for values, sops_ for metadata)
    # Note: SOPS encrypts comments too, so #ENC[ is valid encrypted content
    if grep -q "ENC\[" "$file" 2>/dev/null; then
        return 0  # Has encrypted values
    fi
    if grep -q "^sops_" "$file" 2>/dev/null; then
        return 0  # Has SOPS metadata
    fi

    # Check for plaintext indicators (# followed by non-ENC content = unencrypted comment)
    if grep -q "^#[^E]" "$file" 2>/dev/null || grep -q "^# " "$file" 2>/dev/null; then
        return 1  # Has plaintext comments
    fi

    return 1  # Default to not encrypted
}

# Decrypt SOPS file to stdout
decrypt_sops_env() {
    local encrypted_file="$1"

    if [ ! -f "$SOPS_KEY_FILE" ]; then
        echo "ERROR: SOPS key file not found at $SOPS_KEY_FILE" >&2
        echo "Run './start-ombudsman.sh init-secrets' to generate a key." >&2
        return 1
    fi

    SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --input-type dotenv --output-type dotenv --decrypt "$encrypted_file"
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

            # Remove invalid .enc file
            rm -f "$ENV_FILE_ENC"
            echo "Removed invalid encrypted file."
            echo ""

            # Offer to run installer for interactive setup
            read -p "Run interactive setup wizard? (Y/n): " setup_choice
            setup_choice="${setup_choice:-Y}"
            if [ "$setup_choice" = "Y" ] || [ "$setup_choice" = "y" ]; then
                SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                if [ -f "$SCRIPT_DIR/install-ombudsman.sh" ]; then
                    echo ""
                    echo "Launching setup wizard..."
                    exec sudo "$SCRIPT_DIR/install-ombudsman.sh" --setup-only
                else
                    echo "ERROR: install-ombudsman.sh not found"
                    exit 1
                fi
            else
                echo ""
                echo "To configure manually:"
                echo "  1. Copy template: cp $TEMPLATE_FILE $ENV_FILE"
                echo "  2. Edit config:   nano $ENV_FILE"
                echo "  3. Start:         ./start-ombudsman.sh start"
            fi
            exit 1
        fi
    elif [ -f "$ENV_FILE" ]; then
        echo "Loading config from: $ENV_FILE"
        set -a
        source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
        set +a
    elif [ -f "$TEMPLATE_FILE" ]; then
        echo ""
        echo "=========================================="
        echo "No configuration found"
        echo "=========================================="
        echo ""

        # Offer to run installer for interactive setup
        read -p "Run interactive setup wizard? (Y/n): " setup_choice
        setup_choice="${setup_choice:-Y}"
        if [ "$setup_choice" = "Y" ] || [ "$setup_choice" = "y" ]; then
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            if [ -f "$SCRIPT_DIR/install-ombudsman.sh" ]; then
                echo ""
                echo "Launching setup wizard..."
                exec sudo "$SCRIPT_DIR/install-ombudsman.sh" --setup-only
            else
                echo "ERROR: install-ombudsman.sh not found"
                exit 1
            fi
        else
            echo ""
            echo "To configure manually:"
            echo "  1. Copy template: cp $TEMPLATE_FILE $ENV_FILE"
            echo "  2. Edit config:   nano $ENV_FILE"
            echo "  3. Start:         ./start-ombudsman.sh start"
            echo ""
            echo "To encrypt secrets after editing:"
            echo "  ./start-ombudsman.sh encrypt-secrets"
        fi
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

# Nuclear option: kill EVERYTHING related to ombudsman
nuke_all_processes() {
    printf "Stopping all ombudsman processes... "

    # Kill by PID files
    for pidfile in "$LOG_DIR/backend.pid" "$LOG_DIR/frontend.pid"; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile" 2>/dev/null)
            [ -n "$PID" ] && sudo kill -9 $PID >/dev/null 2>&1 || true
            rm -f "$pidfile" 2>/dev/null
        fi
    done

    # Kill processes silently
    sudo pkill -9 -f "uvicorn main:app" >/dev/null 2>&1 || true
    sudo pkill -9 -f "uvicorn.*${BACKEND_PORT:-8001}" >/dev/null 2>&1 || true
    sudo pkill -9 -f "vite.*preview" >/dev/null 2>&1 || true
    sudo pkill -9 -f "node.*${FRONTEND_PORT:-3000}" >/dev/null 2>&1 || true
    sudo fuser -k ${BACKEND_PORT:-8001}/tcp >/dev/null 2>&1 || true
    sudo fuser -k ${FRONTEND_PORT:-3000}/tcp >/dev/null 2>&1 || true

    sleep 2
    rm -f "$LOG_DIR/backend.pid" "$LOG_DIR/frontend.pid" >/dev/null 2>&1 || true
    printf "Done.\n"
}

kill_process_on_port() {
    local port=$1
    local max_attempts=5
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        # Try multiple methods to find processes on port
        local pids=""

        # Method 1: fuser -k is the most reliable - just kill directly
        if command -v fuser &>/dev/null; then
            sudo fuser -k $port/tcp 2>/dev/null || true
            sleep 1
        fi

        # Method 2: lsof (try with sudo first for better visibility)
        if command -v lsof &>/dev/null; then
            pids=$(sudo lsof -t -i:$port 2>/dev/null | tr '\n' ' ')
            if [ -z "$pids" ]; then
                pids=$(lsof -t -i:$port 2>/dev/null | tr '\n' ' ')
            fi
        fi

        # Method 3: fuser to get PIDs
        if [ -z "$pids" ] && command -v fuser &>/dev/null; then
            pids=$(sudo fuser $port/tcp 2>/dev/null | tr -s ' ')
            if [ -z "$pids" ]; then
                pids=$(fuser $port/tcp 2>/dev/null | tr -s ' ')
            fi
        fi

        # Method 4: ss + awk
        if [ -z "$pids" ] && command -v ss &>/dev/null; then
            pids=$(sudo ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | tr '\n' ' ')
        fi

        # Method 5: netstat fallback
        if [ -z "$pids" ] && command -v netstat &>/dev/null; then
            pids=$(sudo netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | tr '\n' ' ')
        fi

        if [ -z "$pids" ]; then
            # No processes found, port is free
            return 0
        fi

        echo "Killing processes on port $port: $pids (attempt $((attempt+1))/$max_attempts)"
        for pid in $pids; do
            # Force kill with sudo
            sudo kill -9 $pid 2>/dev/null || true
        done

        sleep 2
        attempt=$((attempt+1))
    done

    # Final check
    if sudo lsof -t -i:$port &>/dev/null 2>&1 || sudo fuser $port/tcp &>/dev/null 2>&1; then
        echo "WARNING: Could not free port $port after $max_attempts attempts"
        return 1
    fi
    return 0
}

create_directories() {
    printf "Creating directories... "
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR/projects"
    mkdir -p "$DATA_DIR/pipelines"
    mkdir -p "$DATA_DIR/results"
    mkdir -p "$DATA_DIR/batch_jobs"
    mkdir -p "$DATA_DIR/workloads"
    mkdir -p "$DATA_DIR/auth"
    printf "Done.\n"
}

start_backend() {
    printf "Starting backend on port %s... " "$BACKEND_PORT"

    # Stop any existing backend by PID first
    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
            sleep 1
        fi
        rm -f "$LOG_DIR/backend.pid"
    fi

    # Kill any process on the backend port
    kill_process_on_port "$BACKEND_PORT"

    # Verify port is actually free
    local port_check_attempts=0
    while [ $port_check_attempts -lt 10 ]; do
        if ! lsof -i:$BACKEND_PORT -t &>/dev/null && ! fuser $BACKEND_PORT/tcp &>/dev/null 2>&1; then
            break
        fi
        sleep 1
        kill_process_on_port "$BACKEND_PORT"
        port_check_attempts=$((port_check_attempts+1))
    done

    if lsof -i:$BACKEND_PORT -t &>/dev/null 2>&1; then
        printf "FAILED\n"
        printf "ERROR: Could not free port %s\n" "$BACKEND_PORT"
        return 1
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
    printf "Done (PID: %s)\n" "$!"
}

start_frontend() {
    printf "Starting frontend on port %s... " "$FRONTEND_PORT"

    # Stop any existing frontend by PID first
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
            sleep 1
        fi
        rm -f "$LOG_DIR/frontend.pid"
    fi

    # Kill any process on the frontend port
    kill_process_on_port "$FRONTEND_PORT"

    # Verify port is actually free
    local port_check_attempts=0
    while [ $port_check_attempts -lt 10 ]; do
        if ! lsof -i:$FRONTEND_PORT -t &>/dev/null && ! fuser $FRONTEND_PORT/tcp &>/dev/null 2>&1; then
            break
        fi
        sleep 1
        kill_process_on_port "$FRONTEND_PORT"
        port_check_attempts=$((port_check_attempts+1))
    done

    if lsof -i:$FRONTEND_PORT -t &>/dev/null 2>&1; then
        printf "FAILED\n"
        printf "ERROR: Could not free port %s\n" "$FRONTEND_PORT"
        return 1
    fi

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        printf "\n  Installing frontend dependencies... "
        npm install --silent 2>/dev/null || npm install
    fi

    # Build if dist doesn't exist
    if [ ! -d "dist" ]; then
        printf "\n  Building frontend... "
        npm run build --silent 2>/dev/null || npm run build
    fi

    nohup npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort \
        > "$LOG_DIR/frontend.log" 2>&1 &

    echo $! > "$LOG_DIR/frontend.pid"
    printf "Done (PID: %s)\n" "$!"
}

stop_backend() {
    echo "Stopping backend..."
    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            # Try graceful kill first
            kill $PID 2>/dev/null || sudo kill $PID 2>/dev/null
            sleep 1
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                echo "Process still running, force killing..."
                kill -9 $PID 2>/dev/null || sudo kill -9 $PID 2>/dev/null
            fi
            echo "Backend stopped (PID: $PID)"
        else
            echo "Backend not running (stale PID file, cleaning up)"
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
            # Try graceful kill first
            kill $PID 2>/dev/null || sudo kill $PID 2>/dev/null
            sleep 1
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                echo "Process still running, force killing..."
                kill -9 $PID 2>/dev/null || sudo kill -9 $PID 2>/dev/null
            fi
            echo "Frontend stopped (PID: $PID)"
        else
            echo "Frontend not running (stale PID file, cleaning up)"
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

clean_stale_pids() {
    # Clean up stale PID files (where process is no longer running)
    local cleaned=0

    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "Removing stale backend PID file (process $PID no longer running)"
            rm -f "$LOG_DIR/backend.pid"
            cleaned=1
        fi
    fi

    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ! ps -p $PID > /dev/null 2>&1; then
            echo "Removing stale frontend PID file (process $PID no longer running)"
            rm -f "$LOG_DIR/frontend.pid"
            cleaned=1
        fi
    fi

    return $cleaned
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
        nuke_all_processes
        create_directories
        start_backend
        sleep 3
        start_frontend
        printf "\n=== Started ===\n"
        printf "Backend:  http://%s:%s\n" "$BACKEND_HOST" "$BACKEND_PORT"
        printf "Frontend: http://%s:%s\n" "$FRONTEND_HOST" "$FRONTEND_PORT"
        ;;
    stop)
        nuke_all_processes
        ;;
    restart)
        nuke_all_processes
        create_directories
        start_backend
        sleep 3
        start_frontend
        printf "\n=== Restarted ===\n"
        printf "Backend:  http://%s:%s\n" "$BACKEND_HOST" "$BACKEND_PORT"
        printf "Frontend: http://%s:%s\n" "$FRONTEND_HOST" "$FRONTEND_PORT"
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
    rebuild)
        printf "\n=== Full Rebuild and Restart ===\n\n"

        # NUKE everything first
        nuke_all_processes

        # Pull latest code
        printf "[1/5] Pulling latest code...\n"
        cd "$BASE_DIR"
        git pull 2>&1 | grep -v "^Already up to date" || true

        # Update Python dependencies
        printf "[2/5] Updating Python dependencies...\n"
        cd "$BACKEND_DIR"
        if [ -f "./venv/bin/pip" ]; then
            ./venv/bin/pip install -r requirements.txt --quiet 2>/dev/null
        fi

        # Update frontend dependencies if needed
        printf "[3/5] Checking frontend dependencies...\n"
        cd "$FRONTEND_DIR"
        if [ ! -d "node_modules" ]; then
            npm install --silent 2>/dev/null
        fi

        # Rebuild frontend
        printf "[4/5] Rebuilding frontend...\n"
        npm run build --silent 2>/dev/null || npm run build

        # Create directories and start
        printf "[5/5] Starting services...\n"
        create_directories
        start_backend
        sleep 3
        start_frontend

        printf "\n=== Rebuild Complete ===\n"
        printf "Backend:  http://%s:%s\n" "$BACKEND_HOST" "$BACKEND_PORT"
        printf "Frontend: http://%s:%s\n" "$FRONTEND_HOST" "$FRONTEND_PORT"
        ;;
    nuke)
        nuke_all_processes
        echo "All processes killed. Run './start-ombudsman.sh start' to start fresh."
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
            AGE_PUBLIC_KEY=$(grep -i "public key:" "$SOPS_KEY_FILE" | cut -d: -f2 | tr -d ' ')
        else
            echo "Generating new age encryption key..."
            mkdir -p "$(dirname "$SOPS_KEY_FILE")"
            age-keygen -o "$SOPS_KEY_FILE" 2>&1 | tee /tmp/age-keygen-output.txt
            chmod 600 "$SOPS_KEY_FILE"
            AGE_PUBLIC_KEY=$(grep -i "public key:" /tmp/age-keygen-output.txt | cut -d: -f2 | tr -d ' ')
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

        if ! has_age; then
            echo "ERROR: age is not installed. Run './start-ombudsman.sh init-secrets' first."
            exit 1
        fi

        # Auto-create age key if it doesn't exist
        if [ ! -f "$SOPS_KEY_FILE" ]; then
            echo "No encryption key found. Generating new age key..."
            mkdir -p "$(dirname "$SOPS_KEY_FILE")"
            if ! age-keygen -o "$SOPS_KEY_FILE" 2>&1 | tee /tmp/age-keygen-output.txt; then
                echo "ERROR: Failed to generate age key"
                rm -f /tmp/age-keygen-output.txt
                exit 1
            fi
            chmod 600 "$SOPS_KEY_FILE"
            AGE_PUBLIC_KEY=$(grep -i "public key:" /tmp/age-keygen-output.txt | cut -d: -f2 | tr -d ' ')
            rm -f /tmp/age-keygen-output.txt
            echo "Age key generated at: $SOPS_KEY_FILE"
            echo ""
            echo "IMPORTANT: Back up this key file! Without it, you cannot decrypt your secrets."
            echo ""
        fi

        # Auto-create .sops.yaml if it doesn't exist
        if [ ! -f "$SOPS_CONFIG" ]; then
            echo "Creating SOPS config..."
            AGE_PUBLIC_KEY=$(grep -i "public key:" "$SOPS_KEY_FILE" | cut -d: -f2 | tr -d ' ')
            if [ -z "$AGE_PUBLIC_KEY" ]; then
                echo "ERROR: Could not extract public key from $SOPS_KEY_FILE"
                exit 1
            fi
            cat > "$SOPS_CONFIG" << EOF
creation_rules:
  - path_regex: .*\.env$
    age: $AGE_PUBLIC_KEY
  - path_regex: .*\.env\.enc$
    age: $AGE_PUBLIC_KEY
EOF
            echo "Created $SOPS_CONFIG"
        fi

        if [ ! -f "$ENV_FILE" ]; then
            echo "ERROR: Config file not found at $ENV_FILE"
            exit 1
        fi

        # SOPS dotenv format doesn't handle comments well
        # Strip comments and empty lines before encryption
        echo "Preparing $ENV_FILE for encryption..."
        CLEAN_ENV_FILE="/tmp/ombudsman-clean.env"
        grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' > "$CLEAN_ENV_FILE"

        if [ ! -s "$CLEAN_ENV_FILE" ]; then
            echo "ERROR: No valid environment variables found after stripping comments"
            rm -f "$CLEAN_ENV_FILE"
            exit 1
        fi

        # Encrypt the cleaned env file
        echo "Encrypting..."
        if ! SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --input-type dotenv --output-type dotenv --encrypt "$CLEAN_ENV_FILE" > "$ENV_FILE_ENC.tmp" 2>/tmp/sops-error.txt; then
            echo "ERROR: Encryption failed"
            cat /tmp/sops-error.txt 2>/dev/null
            rm -f "$ENV_FILE_ENC.tmp" /tmp/sops-error.txt "$CLEAN_ENV_FILE"
            exit 1
        fi
        rm -f /tmp/sops-error.txt "$CLEAN_ENV_FILE"

        # Verify the encrypted file has content
        if [ ! -s "$ENV_FILE_ENC.tmp" ]; then
            echo "ERROR: Encrypted file is empty"
            rm -f "$ENV_FILE_ENC.tmp"
            exit 1
        fi

        # Verify encryption markers are present
        if ! grep -q "ENC\[" "$ENV_FILE_ENC.tmp" 2>/dev/null; then
            echo "ERROR: Encryption produced invalid output (no ENC markers)"
            rm -f "$ENV_FILE_ENC.tmp"
            exit 1
        fi

        # Move temp file to final location
        mv "$ENV_FILE_ENC.tmp" "$ENV_FILE_ENC"

        echo ""
        echo "=========================================="
        echo "Encryption complete!"
        echo "=========================================="
        echo ""
        echo "Encrypted file: $ENV_FILE_ENC"
        echo ""
        echo "NOTE: Comments are stripped during encryption."
        echo "      Keep your plaintext file as reference if needed."
        echo ""
        echo "You can safely delete the plaintext file if desired:"
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
        SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --input-type dotenv --output-type dotenv --decrypt "$ENV_FILE_ENC" > "$ENV_FILE"
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

        # Determine which file to edit (use nano as default editor)
        export EDITOR="${EDITOR:-nano}"

        if [ -f "$ENV_FILE_ENC" ]; then
            echo "Opening encrypted file for editing with $EDITOR..."
            echo "(File will be decrypted, edited, then re-encrypted automatically)"
            echo ""
            SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$SOPS_CONFIG" --input-type dotenv --output-type dotenv "$ENV_FILE_ENC"
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
    reconfigure)
        echo "=========================================="
        echo "Reconfigure Ombudsman"
        echo "=========================================="
        echo ""
        echo "This will run the setup wizard to update configuration."
        echo "Services will be restarted after configuration."
        echo ""
        read -p "Continue? (Y/n): " confirm
        if [[ "$confirm" =~ ^[Nn] ]]; then
            echo "Aborted."
            exit 0
        fi

        # Stop services first
        echo ""
        echo "Stopping services..."
        sudo systemctl stop ombudsman-backend ombudsman-frontend 2>/dev/null || true

        # Run the install script with --setup-only flag
        echo ""
        INSTALL_SCRIPT="$SCRIPT_DIR/install-ombudsman.sh"
        if [ ! -f "$INSTALL_SCRIPT" ]; then
            echo "ERROR: Install script not found at $INSTALL_SCRIPT"
            exit 1
        fi

        # Run setup wizard
        bash "$INSTALL_SCRIPT" --setup-only

        # Restart services
        echo ""
        echo "Starting services..."
        sudo systemctl start ombudsman-backend ombudsman-frontend

        echo ""
        echo "=========================================="
        echo "Reconfiguration complete!"
        echo "=========================================="
        echo ""
        echo "Check status: ./start-ombudsman.sh status"
        echo ""
        ;;
    help)
        echo "Ombudsman Validation Studio - Command Reference"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Service Commands:"
        echo "  start              Start backend and frontend (kills existing first)"
        echo "  stop               Stop all services (nuclear kill)"
        echo "  restart            Restart all services (nuclear kill + start)"
        echo "  rebuild            Git pull + rebuild frontend + restart (RECOMMENDED)"
        echo "  nuke               NUCLEAR: Kill ALL ombudsman processes on ports"
        echo "  status             Show service status"
        echo "  logs               Show recent logs"
        echo "  backend            Start only the backend"
        echo "  frontend           Start only the frontend"
        echo ""
        echo "Setup Commands:"
        echo "  reconfigure        Run setup wizard to update config and restart services"
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
        echo "Usage: $0 {start|stop|restart|rebuild|nuke|status|logs|backend|frontend|reconfigure|setup-auth|rebuild-frontend|enable-service|disable-service|update|init-secrets|encrypt-secrets|decrypt-secrets|edit-secrets|help}"
        exit 1
        ;;
esac
