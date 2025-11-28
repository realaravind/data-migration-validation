from fastapi import APIRouter
from core_adapter import run_validations

router = APIRouter()

@router.post("/validate")
def validate_rules(payload: dict):
    config = payload.get("config", {})
    return run_validations(config)