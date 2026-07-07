from datetime import datetime

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator

PROJECT_ID = "loom-insights"
DATASET = "warehouse"
TEMP_TABLE = "temp_weekly_brand_sales"

default_args = {
    'owner': 'airflow',
    'retries': 1,
}

with DAG(
    dag_id='export_weekly_brand_sales',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=['export', 'bigquery', 'gcs'],
) as dag:

    # 1. Run your SQL and save to a temp table
    bq_query = BigQueryInsertJobOperator(
        task_id="run_weekly_brand_sales_query",
        configuration={
            "query": {
                "query": """
                    SELECT
                      product_brand,
                      EXTRACT(WEEK FROM DATE(PARSE_DATE('%Y%m%d',
                                                      CAST(
                                                          date_key AS STRING)))) AS week,

                      EXTRACT(YEAR FROM DATE(PARSE_DATE('%Y%m%d',
                                                      CAST(date_key AS STRING)))) AS year,
                      SUM(revenue) AS total_weekly_sales
                    FROM `loom-insights.warehouse.transactions_mart`
                    GROUP BY
                      product_brand,
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

    # 2. Export the temp table to GCS
    export_to_gcs = BigQueryToGCSOperator(
        task_id='export_temp_table_to_gcs',
        source_project_dataset_table=f"{PROJECT_ID}.{DATASET}.{TEMP_TABLE}",
        destination_cloud_storage_uris=[
            'gs://weekly-insights-data/weekly_brand_sales_{{ ds }}.parquet'
        ],
        export_format='PARQUET',
        gcp_conn_id='gcp-default',
    )

    bq_query >> export_to_gcs
