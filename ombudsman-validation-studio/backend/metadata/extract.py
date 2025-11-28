from fastapi import APIRouter
import sqlalchemy
import sys, os

router = APIRouter()

# Optional reuse of Ombudsman Core extractor
CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ombudsman-core"))
sys.path.append(CORE_PATH)

try:
    from ombudsman_core.metadata.extractor import extract_schema
    CORE_AVAILABLE = True
except:
    CORE_AVAILABLE = False


@router.post("/extract")
def extract_metadata(payload: dict):
    connection = payload.get("connection", "")
    table = payload.get("table", "")

    # Use Ombudsman Core extractor if available
    if CORE_AVAILABLE:
        try:
            cols = extract_schema(connection, table)
            return {"columns": cols}
        except Exception:
            pass

    # Fallback: Use SQLAlchemy
    try:
        engine = sqlalchemy.create_engine(connection)
        meta = sqlalchemy.MetaData()
        meta.reflect(bind=engine)

        if table not in meta.tables:
            return {"columns": [], "error": f"Table '{table}' not found"}

        cols = [c.name for c in meta.tables[table].columns]
        return {"columns": cols}

    except Exception as e:
        return {"columns": [], "error": str(e)}