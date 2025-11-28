from fastapi import APIRouter
from core_adapter import generate_mapping

router = APIRouter()

@router.post("/suggest")
def suggest_mapping(payload: dict):
    source = payload.get("source", [])
    target = payload.get("target", [])
    return generate_mapping(source, target)