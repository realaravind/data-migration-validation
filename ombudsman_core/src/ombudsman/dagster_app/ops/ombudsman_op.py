import subprocess
import os
from dagster import op, Failure

# Load Ombudsman config
from ombudsman.config.environment import load_environment
from ombudsman.notifications.email_alerts import send_failure_email


@op
def run_ombudsman_pipeline(context, pipeline_path: str):
    docker_image = "ombudsman:latest"

    cfg, _ = load_environment()
    alert_email = cfg.get("notifications", {}).get("email")

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{os.getcwd()}/pipelines:/app/pipelines",
        "-v", f"{os.getcwd()}/config:/app/config",
        docker_image,
        "validate", pipeline_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    context.log.info(result.stdout)

    if result.returncode != 0:

        if alert_email:
            send_failure_email(
                to=alert_email,
                pipeline_name=pipeline_path,
                errors=result.stderr or "Unknown error"
            )
            context.log.info(f"Failure email sent → {alert_email}")

        raise Failure(f"Ombudsman pipeline failed: {pipeline_path}")

    return result.stdout