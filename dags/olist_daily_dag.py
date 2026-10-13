"""
Bonus: Airflow DAG that runs the Olist pipeline once a day.

Copy (or symlink) this file into your Airflow dags/ folder and set the environment variable
OLIST_PROJECT_DIR to the folder that contains run_pipeline.py. Needs: pip install apache-airflow
(Airflow is NOT in requirements.txt because the pipeline itself does not need it.)

Tasks:   check_inputs  ->  run_pipeline
  * run_pipeline calls run_pipeline.py; if a data quality check fails the script exits with code 2,
    BashOperator marks the task failed, Airflow retries once and then sends the failure alert.
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = os.environ.get("OLIST_PROJECT_DIR", "/opt/airflow/olist-pipeline")

default_args = {
    "owner": "data-team",
    "retries": 1,                            # one retry, e.g. if the DB file was briefly locked
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="olist_daily_pipeline",
    description="Raw load -> staging -> mart -> data quality checks",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="@daily",                       # (Airflow < 2.4 uses schedule_interval="@daily")
    catchup=False,                           # the pipeline rebuilds everything, no need to backfill
    max_active_runs=1,                       # never two runs writing the same SQLite file
    tags=["olist", "assignment"],
) as dag:

    check_inputs = BashOperator(
        task_id="check_inputs",
        bash_command=f'test -d "{PROJECT_DIR}/data" && ls "{PROJECT_DIR}/data"/*.csv > /dev/null',
    )

    run_pipeline = BashOperator(
        task_id="run_pipeline",
        bash_command=f'cd "{PROJECT_DIR}" && python run_pipeline.py',
    )

    check_inputs >> run_pipeline
