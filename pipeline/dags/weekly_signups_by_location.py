from datetime import datetime

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator

PROJECT_ID = "loom-insights"
DATASET = "warehouse"
TEMP_TABLE = "temp_weekly_signups_by_location"

default_args = {
    "owner": "airflow",
    "retries": 1,
}

with DAG(
    dag_id="weekly_signups_by_location",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,  # Set to your desired schedule
    catchup=False,
    tags=["export", "bigquery", "gcs"],
) as dag:
    bq_query = BigQueryInsertJobOperator(
        task_id="run_weekly_signups_by_location_query",
        configuration={
            "query": {
                "query": """
                    SELECT
                        city,
                        EXTRACT(WEEK FROM registration_date) AS week,
                        EXTRACT(YEAR FROM registration_date) AS year,
                        COUNT(*) AS total_signups
                    FROM
                        `loom-insights.warehouse.stg_users`
                    WHERE
                        registration_date IS NOT NULL
                    GROUP BY
                        city,
                        year,
                        week
                """,
                "destinationTable": {
                    "projectId": PROJECT_ID,
                    "datasetId": DATASET,
                    "tableId": TEMP_TABLE,
                },
                "writeDisposition": "WRITE_TRUNCATE",
                "useLegacySql": False,
            }
        },
        gcp_conn_id="gcp-default",
    )

    export_to_gcs = BigQueryToGCSOperator(
        task_id="export_temp_table_to_gcs",
        source_project_dataset_table=f"{PROJECT_ID}.{DATASET}.{TEMP_TABLE}",
        destination_cloud_storage_uris=[
            "gs://weekly-insights-data/weekly_signups_by_location_{{ ds }}.parquet"
        ],
        export_format="PARQUET",
        gcp_conn_id="gcp-default",
    )

    bq_query >> export_to_gcs
