# src/ombudsman/pipeline/pipeline_runner.py
'''
Executes an entire ordered validation suite.

''' 


# src/ombudsman/pipeline/pipeline_runner.py
'''
Executes an entire ordered validation suite.
'''

from ombudsman.connections.snowflake_conn import get_snowflake_conn
from datetime import datetime
import asyncio

# Import the broadcast helper from your FastAPI app
# Adjust the path if app.py is elsewhere
from app import ws_broadcast  


class PipelineRunner:
    def __init__(self, executor, logger):
        self.executor = executor
        self.logger = logger

        # create a single Snowflake connection for the run
        self.snow_conn = get_snowflake_conn()
        self.cursor = self.snow_conn.cursor()

    def _write_result_to_snowflake(self, pipeline_name, result):
        self.cursor.execute("""
            INSERT INTO OMBUDSMAN_RESULTS (PIPELINE_NAME, STEP_NAME, STATUS, MESSAGE)
            VALUES (%s, %s, %s, %s)
        """, (
            pipeline_name,
            result.step,
            result.status,
            result.message
        ))
        self.snow_conn.commit()

    async def _broadcast_result(self, pipeline_name, result):
        """Send WebSocket update for one step."""
        await ws_broadcast({
            "pipeline": pipeline_name,
            "step": result.step,
            "status": result.status,
            "message": result.message,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })

    def run(self, pipeline_def, pipeline_name="UNKNOWN_PIPELINE"):
        results = []

        for step in pipeline_def:
            # run the validation step
            res = self.executor.run_step(step)
            results.append(res)

            # normal logging
            self.logger.log(res.to_dict())

            # write into Snowflake database
            self._write_result_to_snowflake(pipeline_name, res)

            # NEW: trigger WebSocket broadcast (non-blocking)
            try:
                asyncio.create_task(
                    self._broadcast_result(pipeline_name, res)
                )
            except RuntimeError:
                # In case no running event loop exists (rare)
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._broadcast_result(pipeline_name, res))
                loop.close()

        return results
@app.get("/users")
def user_admin(request: Request, user=Depends(require_role(["admin"]))):
    cur = get_snowflake_conn().cursor()
    cur.execute("SELECT USERNAME, ROLE FROM OMBUDSMAN_USERS ORDER BY USERNAME")
    users = cur.fetchall()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users
    })
 @app.post("/users/add")
def user_add(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    user=Depends(require_role(["admin"]))
):
    hash_pw = hash_password(password)
    cur = get_snowflake_conn().cursor()
    cur.execute("""
        INSERT INTO OMBUDSMAN_USERS (USERNAME, PASSWORD_HASH, ROLE)
        VALUES (%s, %s, %s)
    """, (username, hash_pw, role))
    return RedirectResponse("/users", status_code=303)
@app.post("/users/delete")
def user_delete(
    request: Request,
    username: str = Form(...),
    user=Depends(require_role(["admin"]))
):
    cur = get_snowflake_conn().cursor()
    cur.execute("DELETE FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    return RedirectResponse("/users", status_code=303)
@app.post("/users/role")
def user_role_update(
    request: Request,
    username: str = Form(...),
    role: str = Form(...),
    user=Depends(require_role(["admin"]))
):
    cur = get_snowflake_conn().cursor()
    cur.execute("UPDATE OMBUDSMAN_USERS SET ROLE=%s WHERE USERNAME=%s", (role, username))
    return RedirectResponse("/users", status_code=303)