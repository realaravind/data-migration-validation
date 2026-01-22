#!/bin/bash
#
# Ombudsman Validation Studio - Startup Script
# Usage: ./start-ombudsman.sh [start|stop|status]
#

# ==============================================
# Load Environment File
# ==============================================
ENV_FILE="${OMBUDSMAN_ENV_FILE:-/data/ombudsman/ombudsman.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/ombudsman.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Config file not found at $ENV_FILE"
    if [ -f "$TEMPLATE_FILE" ]; then
        echo "Copying template from $TEMPLATE_FILE..."
        cp "$TEMPLATE_FILE" "$ENV_FILE"
        echo ""
        echo "=========================================="
        echo "IMPORTANT: Edit your config file!"
        echo "=========================================="
        echo "Run: nano $ENV_FILE"
        echo "Update your database credentials, then run this script again."
        echo "=========================================="
        echo ""
        exit 1
    else
        echo "Error: Template file not found at $TEMPLATE_FILE"
        exit 1
    fi
fi

echo "Loading config from: $ENV_FILE"
# Export all variables from .env file (skip comments and empty lines)
set -a
source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
set +a

# ==============================================
# Configuration - Defaults (overridden by .env)
# ==============================================
BASE_DIR="${BASE_DIR:-/data/ombudsman}"
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

# ==============================================
# Functions
# ==============================================

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

    if [ -f "$LOG_DIR/backend.pid" ]; then
        PID=$(cat "$LOG_DIR/backend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Backend already running (PID: $PID)"
            return
        fi
    fi

    cd "$BACKEND_DIR"
    nohup ./venv/bin/python -m uvicorn main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        > "$LOG_DIR/backend.log" 2>&1 &

    echo $! > "$LOG_DIR/backend.pid"
    echo "Backend started (PID: $!)"
    echo "Backend log: $LOG_DIR/backend.log"
}

start_frontend() {
    echo "Starting frontend..."

    if [ -f "$LOG_DIR/frontend.pid" ]; then
        PID=$(cat "$LOG_DIR/frontend.pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Frontend already running (PID: $PID)"
            return
        fi
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

    nohup npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
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
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|backend|frontend}"
        exit 1
        ;;
esac
