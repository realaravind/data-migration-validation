from fastapi import APIRouter
from core_adapter import get_metadata

router = APIRouter()

@router.post("/extract")
def extract_metadata(payload: dict):
    conn = payload.get("connection")
    table = payload.get("table")
    return get_metadata(conn, table)