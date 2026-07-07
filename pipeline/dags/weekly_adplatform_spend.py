from datetime import datetime

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator

PROJECT_ID = "loom-insights"
DATASET = "warehouse"
TEMP_TABLE = "temp_weekly_adplatform_spend"

default_args = {
    'owner': 'airflow',
    'retries': 1,
}

with DAG(
    dag_id='weekly_adplatform_spend',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=['export', 'bigquery', 'gcs'],
) as dag:

    bq_query = BigQueryInsertJobOperator(
        task_id="run_weekly_adplatform_spend_query",
        configuration={
            "query": {
                "query": """
                    SELECT
                      ad_platform,
                      EXTRACT(WEEK FROM date) AS week,
                      EXTRACT(YEAR FROM date) AS year,
                      ROUND(SUM(cost), 2) AS weekly_cost,
                      SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) AS weekly_ctr,
                      SAFE_DIVIDE(SUM(cost), NULLIF(SUM(clicks), 0)) AS weekly_cpc
                    FROM `loom-insights.warehouse.stg_adplatform_data_unpivoted`
                    GROUP BY
                      ad_platform,
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
        gcp_conn_id='gcp-default',
    )

    export_to_gcs = BigQueryToGCSOperator(
        task_id='export_temp_table_to_gcs',
        source_project_dataset_table=f"{PROJECT_ID}.{DATASET}.{TEMP_TABLE}",
        destination_cloud_storage_uris=[
            'gs://weekly-insights-data/weekly_adplatform_spend_{{ ds }}.parquet'
        ],
        export_format='PARQUET',
        gcp_conn_id='gcp-default',
    )

    bq_query >> export_to_gcs
