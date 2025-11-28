from dagster import job
from dagster_app.ops.ombudsman_op import run_ombudsman_pipeline


@job
def ombudsman_job():
    run_ombudsman_pipeline(pipeline_path="pipelines/validate_sales.yaml")