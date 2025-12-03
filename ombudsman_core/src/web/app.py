from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware
from ombudsman.core.snowflake_conn import SnowflakeConn
from ombudsman.pipeline.pipeline_runner import PipelineRunner
# from ombudsman.executor import Executor  # TODO: Find correct path
# from ombudsman.logger import Logger  # TODO: Find correct path
import hashlib
import yaml
from fastapi import WebSocket, WebSocketDisconnect
import logging

# Setup basic logging
logger = logging.getLogger(__name__)

active_websockets = []


def get_user_role(username):
    try:
        conn = SnowflakeConn()
        cursor = conn.cur
        cursor.execute("SELECT ROLE FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
        row = cursor.fetchone()
        return row[0] if row else "viewer"
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return "viewer"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="CHANGE_ME")

templates = Jinja2Templates(directory="src/web/templates")


# ------------------------------------------------------------------------------
# AUTH + RBAC
# ------------------------------------------------------------------------------

def hash_password(pwd: str):
    return hashlib.sha256(pwd.encode()).hexdigest()

# TEMP — until Snowflake user table is added
USERS = {
    "admin": hash_password("admin123")
}

def require_login(request: Request):
    if "user" not in request.session:
        raise HTTPException(status_code=401)
    return request.session["user"]


def require_role(roles):
    def wrapper(request: Request):
        if "user" not in request.session:
            raise HTTPException(status_code=401)

        role = request.session.get("role", "viewer")
        if role not in roles:
            raise HTTPException(status_code=403)
        return request.session["user"]

    return wrapper


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_snowflake_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT PASSWORD_HASH, ROLE FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    row = cursor.fetchone()

    if not row:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    stored_hash, role = row
    if stored_hash != hash_password(password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    # Save username & role into session
    request.session["user"] = username
    request.session["role"] = role

    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ------------------------------------------------------------------------------
# FETCH RESULTS
# ------------------------------------------------------------------------------

def fetch_results(filters=None):
    conn = get_snowflake_conn()
    cursor = conn.cursor()

    query = """
        SELECT PIPELINE_NAME, STEP_NAME, STATUS, MESSAGE, RUN_TIMESTAMP
        FROM OMBUDSMAN_RESULTS
        WHERE 1=1
    """

    params = []

    if filters:
        if filters.get("pipeline"):
            query += " AND PIPELINE_NAME = %s"
            params.append(filters["pipeline"])
        if filters.get("status"):
            query += " AND STATUS = %s"
            params.append(filters["status"])
        if filters.get("start_date"):
            query += " AND RUN_TIMESTAMP >= %s"
            params.append(filters["start_date"])
        if filters.get("end_date"):
            query += " AND RUN_TIMESTAMP <= %s"
            params.append(filters["end_date"])

    query += " ORDER BY RUN_TIMESTAMP DESC LIMIT 200"

    cursor.execute(query, params)
    return cursor.fetchall()


# ------------------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user=Depends(require_login),
    pipeline: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
):
    filters = {
        "pipeline": pipeline,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
    }

    rows = fetch_results(filters)
    role = get_user_role(request.session["user"])
   
    return templates.TemplateResponse(
    "index.html",
    {
        "request": request,
        "rows": rows,
        "role": role
    }
)


# ------------------------------------------------------------------------------
# CHARTS
# ------------------------------------------------------------------------------

@app.get("/chart-data")
def chart_data():
    conn = get_snowflake_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT STATUS, COUNT(*) 
        FROM OMBUDSMAN_RESULTS 
        GROUP BY STATUS
    """)
    rows = cursor.fetchall()
    return {"labels": [r[0] for r in rows], "values": [r[1] for r in rows]}


@app.get("/pipeline-trend")
def pipeline_trend():
    cursor = get_snowflake_conn().cursor()
    cursor.execute("""
        SELECT PIPELINE_NAME, 
               SUM(CASE WHEN STATUS='PASS' THEN 1 ELSE 0 END),
               SUM(CASE WHEN STATUS='FAIL' THEN 1 ELSE 0 END)
        FROM OMBUDSMAN_RESULTS
        GROUP BY PIPELINE_NAME
    """)
    rows = cursor.fetchall()
    return {
        "pipelines": [r[0] for r in rows],
        "pass": [r[1] for r in rows],
        "fail": [r[2] for r in rows]
    }


@app.get("/chart-history")
def chart_history():
    cursor = get_snowflake_conn().cursor()
    cursor.execute("""
        SELECT DATE(RUN_TIMESTAMP), COUNT(*)
        FROM OMBUDSMAN_RESULTS
        GROUP BY DATE(RUN_TIMESTAMP)
        ORDER BY DATE(RUN_TIMESTAMP)
    """)
    rows = cursor.fetchall()
    return {"dates": [str(r[0]) for r in rows], "counts": [r[1] for r in rows]}


# ------------------------------------------------------------------------------
# UPLOAD PIPELINE
# ------------------------------------------------------------------------------

@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
def upload_pipeline(
    file: UploadFile = File(...),
    user: str = Form("unknown"),
    logged_in=Depends(require_login),
):
    yaml_data = file.file.read().decode()
    cursor = get_snowflake_conn().cursor()
    cursor.execute(
        """
        INSERT INTO OMBUDSMAN_PIPELINES (NAME, YAML_CONTENT, UPLOADED_BY)
        VALUES (%s, %s, %s)
    """,
        (file.filename, yaml_data, user),
    )
    return {"status": "uploaded", "file": file.filename}

@app.get("/get_pipeline")
def get_pipeline(name: str, user=Depends(require_login)):
    cursor = get_snowflake_conn().cursor()
    cursor.execute("SELECT YAML_CONTENT FROM OMBUDSMAN_PIPELINES WHERE NAME=%s", (name,))
    row = cursor.fetchone()
    if not row:
        return {"yaml": "Pipeline not found"}
    return {"yaml": row[0]}

import json
import asyncio

async def ws_broadcast(data: dict):
    dead = []
    for ws in active_websockets:
        try:
            await ws.send_text(json.dumps(data))
        except:
            dead.append(ws)
    for ws in dead:
        active_websockets.remove(ws)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_websockets.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(ws)

# ------------------------------------------------------------------------------
# RUN PIPELINE
# ------------------------------------------------------------------------------

@app.post("/run_pipeline")
def run_pipeline(
    name: str = Form(),
    user=Depends(require_login)
):
    conn = get_snowflake_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT YAML_CONTENT FROM OMBUDSMAN_PIPELINES WHERE NAME = %s", (name,))
    row = cursor.fetchone()
    if not row:
        return {"status": "error", "message": "Pipeline not found"}

    pipeline_def = yaml.safe_load(row[0])
    runner = PipelineRunner(Executor(), Logger())
    runner.run(pipeline_def, pipeline_name=name)

    return {"status": "executed", "pipeline": name}


# ------------------------------------------------------------------------------
# SIMPLE SCHEDULER
# ------------------------------------------------------------------------------

@app.get("/schedule")
def schedule_job(user=Depends(require_login)):
    import threading

    def job():
        cursor = get_snowflake_conn().cursor()
        cursor.execute("SELECT NAME, YAML_CONTENT FROM OMBUDSMAN_PIPELINES")
        pipelines = cursor.fetchall()

        runner = PipelineRunner(Executor(), Logger())

        for name, yaml_text in pipelines:
            pipeline_def = yaml.safe_load(yaml_text)
            runner.run(pipeline_def, pipeline_name=name)

    threading.Thread(target=job).start()
    return {"status": "scheduled run started"}

