/*
===================================================================================
MODEL: dim_source
===================================================================================

PURPOSE:
    Source dimension table for marketing attribution analysis.
    Standardizes traffic source classifications for granular source-level tracking.

SOURCE:
    - {{ ref('stg_sessions') }}

GRAIN:
    One row per unique traffic source

KEY ATTRIBUTES:
    - Traffic source identification
    - Source category classification
    - Automated channel categorization
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['source_key'], 'type': 'btree'}
    ]
) }}

WITH source_combinations AS (
    SELECT DISTINCT
        traffic_source AS source,

        -- Get first occurrence timestamp for metadata
        MIN(dbt_valid_from) AS first_seen_at,
        MAX(dbt_updated_at) AS last_seen_at

    FROM {{ ref('stg_sessions') }}
    WHERE traffic_source IS NOT NULL
    GROUP BY 1
),

source_dimension AS (
    SELECT
        -- Primary key: simple integer ID
        ROW_NUMBER() OVER (ORDER BY source) AS source_key,

        source,

        -- dbt metadata
        last_seen_at AS dbt_updated_at,
        first_seen_at AS dbt_created_at

    FROM source_combinations
)

SELECT * FROM source_dimension
