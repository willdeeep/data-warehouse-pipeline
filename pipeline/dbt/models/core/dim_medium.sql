/*
===================================================================================
MODEL: dim_medium
===================================================================================

PURPOSE:
    Medium dimension table for marketing attribution analysis.
    Standardizes traffic medium classifications for granular medium-level tracking.

SOURCE:
    - {{ ref('stg_sessions') }}

GRAIN:
    One row per unique traffic medium

KEY ATTRIBUTES:
    - Traffic medium identification
    - Medium category classification
    - Automated channel categorization
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['medium_key'], 'type': 'btree'},
        {'columns': ['medium_category'], 'type': 'btree'}
    ]
) }}

WITH medium_combinations AS (
    SELECT DISTINCT
        traffic_medium AS medium,

        -- Standardize medium categories for reporting
        CASE
            WHEN LOWER(traffic_medium) IN ('organic') THEN 'Organic'
            WHEN LOWER(traffic_medium) IN ('cpc', 'ppc', 'paid') THEN 'Paid Search'
            WHEN LOWER(traffic_medium) IN ('social', 'social-network', 'social-media') THEN 'Social'
            WHEN LOWER(traffic_medium) IN ('email', 'newsletter') THEN 'Email'
            WHEN LOWER(traffic_medium) IN ('display', 'banner') THEN 'Display'
            WHEN LOWER(traffic_medium) IN ('affiliate', 'referral') THEN 'Referral'
            WHEN LOWER(traffic_medium) IN ('video') THEN 'Video'
            WHEN LOWER(traffic_medium) IN ('(none)', 'direct') THEN 'Direct'
            WHEN LOWER(traffic_medium) IN ('push', 'notification') THEN 'Push'
            WHEN LOWER(traffic_medium) IN ('sms', 'text') THEN 'SMS'
            ELSE 'Other'
        END AS medium_category,

        -- Get first occurrence timestamp for metadata
        MIN(dbt_valid_from) AS first_seen_at,
        MAX(dbt_updated_at) AS last_seen_at

    FROM {{ ref('stg_sessions') }}
    WHERE traffic_medium IS NOT NULL
    GROUP BY 1
),

medium_dimension AS (
    SELECT
        -- Primary key: simple integer ID
        ROW_NUMBER() OVER (ORDER BY medium) AS medium_key,

        medium,
        medium_category,

        -- dbt metadata
        last_seen_at AS dbt_updated_at,
        first_seen_at AS dbt_created_at

    FROM medium_combinations
)

SELECT * FROM medium_dimension
