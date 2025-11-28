from fastapi import APIRouter
from core_adapter import run_pipeline
import yaml
import tempfile

router = APIRouter()

@router.post("/run")
def execute_pipeline(payload: dict):
    yaml_content = payload.get("yaml_content")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as f:
        f.write(yaml_content)
        temp_path = f.name

    result = run_pipeline(temp_path)
    return result