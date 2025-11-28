from fastapi import APIRouter
import sys, os, json

# Optional Ombudsman Core integration
CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ombudsman-core"))
sys.path.append(CORE_PATH)

try:
    from ombudsman_core.pipeline.builder import build_pipeline
    CORE_AVAILABLE = True
except:
    CORE_AVAILABLE = False

router = APIRouter()

SAVE_PATH = "pipeline_suggestions.json"


def ai_fallback_suggestions(metadata):
    src = metadata.get("source", [])
    suggestions = []

    if "id" in src:
        suggestions.append("Validate ID uniqueness")

    if "email" in src:
        suggestions.append("Check email format")

    if any("date" in c.lower() for c in src):
        suggestions.append("Validate date formats")

    if len(src) > 10:
        suggestions.append("Run completeness & null checks")

    if not suggestions:
        suggestions.append("No strong recommendations. Review manually.")

    return suggestions


@router.post("/generate")
def generate_pipeline(payload: dict):
    metadata = payload.get("metadata", {})

    if CORE_AVAILABLE:
        try:
            return {"steps": build_pipeline(metadata)}
        except Exception:
            pass

    return {"steps": ai_fallback_suggestions(metadata)}


@router.post("/save")
def save_pipeline(payload: dict):
    steps = payload["steps"]
    with open(SAVE_PATH, "w") as f:
        json.dump(steps, f, indent=2)
    return {"status": "saved", "path": SAVE_PATH}


@router.post("/load")
def load_pipeline():
    if not os.path.exists(SAVE_PATH):
        return {"steps": []}
    with open(SAVE_PATH, "r") as f:
        return {"steps": json.load(f)}