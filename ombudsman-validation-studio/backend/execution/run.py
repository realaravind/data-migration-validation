from fastapi import APIRouter
import subprocess
import sys
import os
import json
from datetime import datetime

router = APIRouter()

LOG_PATH = "execution_logs.json"

# Optional Ombudsman Core integration
CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ombudsman-core"))
sys.path.append(CORE_PATH)

try:
    from ombudsman_core.engine.run_pipeline import run_pipeline
    CORE_AVAILABLE = True
except:
    CORE_AVAILABLE = False


def write_log(entry):
    logs = []
    if os.path.exists(LOG_PATH):
        try:
            logs = json.load(open(LOG_PATH, "r"))
        except:
            logs = []

    logs.append(entry)
    with open(LOG_PATH, "w") as f:
        json.dump(logs, f, indent=2)


@router.post("/run")
def run_execution(payload: dict):
    pipeline = payload.get("pipeline", [])
    metadata = payload.get("metadata", {})

    timestamp = datetime.utcnow().isoformat()

    # If Ombudsman Core executor exists
    if CORE_AVAILABLE:
        try:
            result = run_pipeline(pipeline, metadata)
            log_entry = {
                "timestamp": timestamp,
                "status": "success",
                "output": result
            }
            write_log(log_entry)
            return log_entry
        except Exception as e:
            log_entry = {
                "timestamp": timestamp,
                "status": "error",
                "output": str(e)
            }
            write_log(log_entry)
            return log_entry

    # Minimal fallback executor
    output = {
        "message": "Core not available. Simulated execution.",
        "pipeline": pipeline,
        "metadata": metadata
    }

    log_entry = {
        "timestamp": timestamp,
        "status": "success",
        "output": output
    }

    write_log(log_entry)
    return log_entry


@router.post("/logs")
def load_logs():
    if not os.path.exists(LOG_PATH):
        return {"logs": []}
    try:
        return {"logs": json.load(open(LOG_PATH))}
    except:
        return {"logs": []}