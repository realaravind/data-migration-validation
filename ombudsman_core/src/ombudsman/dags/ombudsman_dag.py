from airflow import DAG
from datetime import datetime

from plugins.ombudsman_operator import OmbudsmanOperator

with DAG(
    "ombudsman_validation_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:

    run_sales = OmbudsmanOperator(
        task_id="validate_sales",
        pipeline_path="pipelines/validate_sales.yaml",
    )