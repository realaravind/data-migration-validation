from fastapi import APIRouter
import os
import json
import sys

# Optional Ombudsman Core integration
CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ombudsman-core"))
sys.path.append(CORE_PATH)

try:
    from ombudsman_core.validation.engine import compile_rules
    CORE_AVAILABLE = True
except:
    CORE_AVAILABLE = False

router = APIRouter()

SAVE_PATH = "rules_saved.json"


@router.post("/save")
def save_rules(payload: dict):
    rules = payload["rules"]

    # Optional pass-through to Ombudsman Core compiler
    if CORE_AVAILABLE:
        try:
            compiled = compile_rules(rules)
            rules = compiled
        except Exception:
            pass

    with open(SAVE_PATH, "w") as f:
        json.dump(rules, f, indent=2)

    return {"status": "saved", "path": SAVE_PATH}


@router.post("/load")
def load_rules():
    if not os.path.exists(SAVE_PATH):
        return {"rules": []}
    with open(SAVE_PATH, "r") as f:
        data = json.load(f)
    return {"rules": data}