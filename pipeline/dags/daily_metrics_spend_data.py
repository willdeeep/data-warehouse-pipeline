"""
Daily Metrics and Spend Data Export Pipeline

This DAG extracts comprehensive advertising spend and performance metrics from the data warehouse,
    combining advertising costs, session data, and transaction information to create a unified daily
metrics report. The pipeline generates a CSV export for further analysis and reporting.

Key Features:
- Aggregates advertising spend data across multiple platforms
- Calculates conversion rates and ROAS (Return on Ad Spend)
- Combines session, transaction, and advertising data
- Exports results to Google Cloud Storage as CSV format
- Handles null values and edge cases in calculations

Data Sources:
- fact_advertising: Platform-specific advertising costs and metrics
- fact_sessions: User session data with source attribution
- fact_transactions: E-commerce transaction data
- dim_ad_platform: Advertising platform reference data
- dim_source: Traffic source reference data

Output Fields:
- date_key: Date of the metrics
- source: Traffic/advertising source
- cost: Total advertising spend
- clicks: Number of ad clicks
- impressions: Number of ad impressions
- daily_transaction_total: Revenue generated
- conversion_rate: Percentage of sessions that converted
- ROAS: Return on Ad Spend percentage

Schedule: Manual trigger (schedule=None)
Export Location: gs://daily-metrics-spend-data/

Author: Data Engineering Team
Last Updated: 2025-06-26
"""

from datetime import datetime

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator

PROJECT_ID = "loom-insights"
DATASET = "warehouse"
TEMP_TABLE = "temp_daily_metrics_spend_data"

default_args = {
    "owner": "airflow",
    "retries": 2,  # Retry failed tasks up to 2 times
}

SQL = """
WITH adplatorm_numbers AS (
    SELECT
    ad.date_key,
    a.platform_name,
    cost,
    clicks,
    impressions
  FROM
    loom-insights.warehouse.fact_advertising AS ad
  LEFT JOIN
    `warehouse.dim_ad_platform` AS a
  ON
    a.platform_key=ad.platform_key
),
    source_join AS (
    SELECT
    n.date_key,
    source_key,
    source,
    n.cost,
    n.impressions,
    n.clicks
  FROM
    `warehouse.dim_source` as s
  LEFT JOIN
    adplatorm_numbers as n
  ON
    s.source=n.platform_name
),
    session_join AS (
    SELECT
    s.date_key,
    s.source_key,
    source,
    cost,
    impressions,
    clicks
  FROM
  source_join AS sj
  LEFT JOIN
    `warehouse.fact_sessions` AS s
  ON
    s.source_key=sj.source_key AND sj.date_key=s.date_key
  order by
    sj.date_key
),
    daily_transaction_total AS(
    SELECT
    t.date_key,
    source,
    ROUND(SUM(transaction_total), 2) as daily_transaction_total,
    count(t.transaction_id) as conversions,
        FROM
    `warehouse.fact_transactions` AS t
  LEFT JOIN
    `warehouse.fact_sessions` as s
  ON
    t.session_id=s.session_id
  LEFT JOIN
    `warehouse.dim_source` as so
  ON
    so.source_key=s.source_key
  GROUP BY
    date_key, source
),
    conversion_rate AS (
    SELECT
    date_key,
    source,
    count(session_id) as session_num
  FROM
    `warehouse.fact_sessions` AS s
  LEFT JOIN
    `dev_warehouse.dim_source` AS so
  ON s.source_key=so.source_key
  GROUP BY date_key, source
)
SELECT
  t.date_key,
      t.source,
      cost,
      clicks,
      impressions,
      daily_transaction_total,
      round(t.conversions / session_num * 100, 2) as conversion_rate,
      CASE WHEN cost=0 then null
  else ROUND(daily_transaction_total / cost * 100, 2) END AS ROAS
FROM
  session_join AS s
LEFT JOIN
  daily_transaction_total AS t
ON
  t.date_key=s.date_key AND t.source=s.source
LEFT JOIN
  conversion_rate AS c
ON
  c.source=s.source AND c.date_key=s.date_key
WHERE
  t.date_key IS NOT NULL
group by
  t.date_key, source, cost, clicks, impressions, daily_transaction_total, session_num, t.conversions
order by
  t.date_key ASC, source ASC
"""

with DAG(
    dag_id="daily_metrics_spend_data",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,  # Set to your desired schedule
    catchup=False,
    tags=["export", "bigquery", "gcs"],
) as dag:
    bq_query = BigQueryInsertJobOperator(
        task_id="run_daily_metrics_spend_data_query",
        configuration={
            "query": {
                "query": SQL,
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
            "gs://daily-metrics-spend-data/daily_metrics_spend_data_{{ ds }}.csv"
        ],
        export_format="CSV",
        gcp_conn_id="gcp-default",
    )

    bq_query >> export_to_gcs
