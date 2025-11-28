import argparse
import yaml

from ..logging.json_logger import JsonLogger
from ..pipeline.step_executor import StepExecutor
from ..pipeline.pipeline_runner import PipelineRunner
from ..core.registry import ValidationRegistry

# Batch 7 imports
from ..config.environment import load_environment
from ..core.connections import get_sql_conn, get_snow_conn

# Email alert import
from ..notifications.email_alerts import send_failure_email

from ombudsman.bootstrap.db_setup import initialize_snowflake_tables
snow_conn = get_snow_conn(cfg)
initialize_snowflake_tables(snow_conn)


def main():
    parser = argparse.ArgumentParser(prog="ombudsman")
    parser.add_argument("command")
    parser.add_argument("pipeline_file")
    args = parser.parse_args()

    if args.command != "validate":
        print("Unknown command:", args.command)
        return

    # Load pipeline YAML file
    pipeline = yaml.safe_load(open(args.pipeline_file))

    # Load config + secrets (Batch 7)
    cfg, secrets = load_environment()

    # Extract notification email from config
    alert_email = cfg.get("notifications", {}).get("email")

    # Initialize registry and auto-register validators
    registry = ValidationRegistry()
    from ..bootstrap import register_validators
    register_validators(registry)

    # Create database connections
    sql_conn = get_sql_conn(cfg)
    snow_conn = get_snow_conn(cfg)

    mapping = pipeline.get("mapping", {})
    metadata = pipeline.get("metadata", {})
    steps = pipeline.get("steps", [])

    executor = StepExecutor(
        registry=registry,
        sql_conn=sql_conn,
        snow_conn=snow_conn,
        mapping=mapping,
        metadata=metadata
    )

    logger = JsonLogger()
    runner = PipelineRunner(executor, logger)

    results = runner.run(steps)

    failures = [r for r in results if r.status in ("FAIL", "ERROR")]

    # Handle failure path
    if failures:

        # Build failure message body
        error_text = "\n".join(
            f"{f.step}: {f.message}" for f in failures
        )

        # If config contains alert email, send notification
        if alert_email:
            try:
                send_failure_email(
                    to=alert_email,
                    pipeline_name=args.pipeline_file,
                    errors=error_text
                )
                print(f"Failure email sent to {alert_email}")
            except Exception as e:
                print(f"Failed to send alert email: {e}")

        exit(1)

    # Success exit
    exit(0)