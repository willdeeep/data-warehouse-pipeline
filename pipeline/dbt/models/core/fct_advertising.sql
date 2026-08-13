/*
===================================================================================
MODEL: fct_advertising
===================================================================================

PURPOSE:
    Advertising fact table for marketing performance analysis.
    Contains ad platform metrics with dimensional foreign keys.

SOURCE:
    - {{ ref('stg_adplatform_data_unpivoted') }}

GRAIN:
    One row per ad platform per date

KEY METRICS:
    - Impressions and clicks
    - Advertising spend
    - Click-through rate (CTR)
    - Cost performance metrics
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['ad_key'], 'type': 'btree'},
        {'columns': ['date_key'], 'type': 'btree'},
        {'columns': ['platform_key'], 'type': 'btree'}
    ]
) }}

WITH advertising_base AS (
    SELECT
        date,
        ad_platform AS platform_name,
        impressions,
        clicks,
        cost,
        cpc,
        dbt_updated_at,
        dbt_valid_from
    FROM {{ ref('stg_adplatform_data_unpivoted') }}
    WHERE date IS NOT NULL
      AND ad_platform IS NOT NULL
),

fact_advertising AS (
    SELECT
        -- Primary key: date + platform
        {{ generate_int_surrogate_key(['date', 'platform_name']) }} AS ad_key,

        -- Date dimension foreign key
        CAST(FORMAT_DATE('%Y%m%d', date) AS INT64) AS date_key,

        -- Platform dimension foreign key
        {{ generate_int_surrogate_key(['platform_name']) }} AS platform_key,

        -- Advertising metrics
        COALESCE(impressions, 0) AS impressions,
        COALESCE(clicks, 0) AS clicks,
        COALESCE(cost, 0.0) AS cost,

        -- Calculated CTR (Click-through rate)
        CASE
            WHEN COALESCE(impressions, 0) > 0
            THEN SAFE_DIVIDE(COALESCE(clicks, 0), COALESCE(impressions, 0))
            ELSE 0.0
        END AS ctr,

        -- dbt metadata
        dbt_updated_at,
        dbt_valid_from AS dbt_created_at

    FROM advertising_base
)

SELECT * FROM fact_advertising
