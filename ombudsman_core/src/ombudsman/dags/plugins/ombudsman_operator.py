from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException
import subprocess
import os

# Load Ombudsman config (Batch 7 loader)
from ombudsman.config.environment import load_environment


class OmbudsmanOperator(BaseOperator):

    @apply_defaults
    def __init__(
        self,
        pipeline_path,
        docker_image="ombudsman:latest",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.pipeline_path = pipeline_path
        self.docker_image = docker_image

        # Load email from Ombudsman config
        cfg, _ = load_environment()
        self.alert_email = cfg.get("notifications", {}).get("email")

    def execute(self, context):
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}/pipelines:/app/pipelines",
            "-v", f"{os.getcwd()}/config:/app/config",
            self.docker_image,
            "validate", self.pipeline_path
        ]

        self.log.info(f"Running Ombudsman pipeline: {self.pipeline_path}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        self.log.info(result.stdout)

        if result.returncode != 0:
            self.log.error(result.stderr or "Pipeline failed.")

            # Send email if configured
            if self.alert_email:
                from ombudsman.notifications.email_alerts import send_failure_email
                send_failure_email(
                    to=self.alert_email,
                    pipeline_name=self.pipeline_path,
                    errors=result.stderr or "Unknown error"
                )
                self.log.info(f"Failure email sent → {self.alert_email}")

            raise AirflowException("Ombudsman pipeline failed")

        return result.stdout