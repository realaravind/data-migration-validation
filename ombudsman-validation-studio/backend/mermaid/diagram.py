from fastapi import APIRouter
import os
import json
import sys

# Optional Ombudsman Core integration
CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ombudsman-core"))
sys.path.append(CORE_PATH)

try:
    from ombudsman_core.pipeline.graph import generate_mermaid
    CORE_AVAILABLE = True
except:
    CORE_AVAILABLE = False

router = APIRouter()

SAVE_PATH = "diagram_saved.mmd"


@router.post("/save")
def save_diagram(payload: dict):
    content = payload["diagram"]
    with open(SAVE_PATH, "w") as f:
        f.write(content)
    return {"status": "saved", "path": SAVE_PATH}


@router.post("/load")
def load_diagram():
    if not os.path.exists(SAVE_PATH):
        return {"diagram": ""}
    with open(SAVE_PATH, "r") as f:
        return {"diagram": f.read()}


@router.post("/auto-generate")
def auto_generate(payload: dict):
    if not CORE_AVAILABLE:
        return {"diagram": "graph TD;\n  A[Core Not Available] --> B[No Auto Generate]"}

    try:
        diagram = generate_mermaid(payload)
        return {"diagram": diagram}
    except Exception as e:
        return {"diagram": f"graph TD;\nError[{str(e)}]"}