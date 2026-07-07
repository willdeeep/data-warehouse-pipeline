from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    dag_id='weekly_etl_ebay',
    default_args=default_args,
    description='Weekly ETL for eBay data',
    schedule='@daily',  # <-- changed from '@weekly' to '@daily'
    start_date=datetime(2024, 6, 1),
    catchup=False,
    tags=['ebay', 'etl'],
) as dag:

    extract_task = BashOperator(
        task_id='extract_raw_data',
        bash_command='cd /opt/airflow/dags && python extract_raw_data.py',
    )

    transform_task = BashOperator(
        task_id='transform_data',
        bash_command='cd /opt/airflow/dags && python transform_data.py',
    )

    extract_task >> transform_task
