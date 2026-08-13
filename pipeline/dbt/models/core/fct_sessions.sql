/*
===================================================================================
MODEL: fct_sessions
===================================================================================

PURPOSE:
    Session fact table for digital analytics and user behavior analysis.
    Contains session-level metrics with dimensional foreign keys.

SOURCES:
    - {{ ref('stg_sessions') }}
    - {{ ref('stg_funnel_events') }}

GRAIN:
    One row per user session

KEY METRICS:
    - Page views per session
    - Add to cart activity
    - Bounce behavior
    - Transaction activity
    - Session duration
    - Source and medium attribution
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['session_id'], 'type': 'btree'},
        {'columns': ['date_key'], 'type': 'btree'},
        {'columns': ['user_crm_id'], 'type': 'btree'}
    ]
) }}

WITH session_base AS (
    SELECT
        session_id,
        start_date,
        end_date,
        session_count,
        user_cookie_id,
        user_crm_id,
        city,
        traffic_source,
        traffic_medium,
        device_category,
        dbt_updated_at,
        dbt_valid_from
    FROM {{ ref('stg_sessions') }}
    WHERE session_id IS NOT NULL
),

-- Aggregate funnel events by session
session_funnel_metrics AS (
    SELECT
        session_id,
        COUNT(*) AS events,
        COUNT(DISTINCT CASE WHEN event_name = 'page_view' THEN 1 ELSE 0 END) AS page_views,
        MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS add_to_cart_flag,
        SUM(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS transaction_count
    FROM {{ ref('stg_funnel_events') }}
    WHERE session_id IS NOT NULL
    GROUP BY 1
),

-- Determine bounce sessions (single page view, no engagement)
session_bounce AS (
    SELECT
        session_id,
        CASE
            WHEN page_views = 1 AND add_to_cart_flag = 0 AND transaction_count = 0
            THEN TRUE
            ELSE FALSE
        END AS bounce_flag
    FROM session_funnel_metrics
),

-- Calculate time between first and last event per session
session_duration AS (
    SELECT
        session_id,
        TIMESTAMP_DIFF(MAX(event_time), MIN(event_time), SECOND) AS session_duration
    FROM
        {{ ref('stg_funnel_events') }}
    WHERE session_id IS NOT NULL
    GROUP BY session_id
),

-- Fact table combining session data with metrics
fact_sessions AS (
    SELECT
        -- Primary key (use session_id directly)
        sb.session_id AS session_id,

        -- User cookie ID (natural key)
        sb.user_cookie_id AS user_cookie_id,

        -- Date dimension foreign key (using start_date)
        CAST(FORMAT_DATE('%Y%m%d', sb.start_date) AS INT64) AS date_key,

        -- User dimension foreign key (now using natural key)
        sb.user_crm_id AS user_crm_id,

        -- Source dimension foreign key (lookup from dim_source)
        ds.source_key AS source_key,

        -- Medium dimension foreign key (lookup from dim_medium)
        dm.medium_key AS medium_key,

        -- Geo dimension foreign key (lookup from dim_geo)
        dg.geo_key AS geo_key,

        -- Device dimension foreign key (lookup from dim_devices)
        dd.device_key AS device_key,

        -- Platform dimension foreign key (lookup from dim_ad_platform)
        dap.platform_key AS platform_key,

        -- Session metrics
        COALESCE(sfm.page_views, 0) AS page_views,
        COALESCE(sfm.add_to_cart_flag = 1, FALSE) AS add_to_cart_flag,
        COALESCE(sb_bounce.bounce_flag, FALSE) AS bounce_flag,
        COALESCE(sfm.transaction_count, 0) AS transaction_count,

        -- Session duration (null for bounced sessions)
        CASE
            WHEN COALESCE(sb_bounce.bounce_flag, FALSE) = TRUE THEN NULL
            ELSE sd.session_duration
        END AS session_duration_seconds,

        -- dbt metadata
        sb.dbt_updated_at,
        sb.dbt_valid_from AS dbt_created_at

    FROM session_base sb
    LEFT JOIN session_funnel_metrics sfm ON sb.session_id = sfm.session_id
    LEFT JOIN session_bounce sb_bounce ON sb.session_id = sb_bounce.session_id
    LEFT JOIN session_duration sd ON sb.session_id = sd.session_id
    LEFT JOIN {{ ref('dim_source') }} ds ON sb.traffic_source = ds.source
    LEFT JOIN {{ ref('dim_medium') }} dm ON sb.traffic_medium = dm.medium
    LEFT JOIN {{ ref('dim_geo') }} dg ON sb.city = dg.city
    LEFT JOIN {{ ref('dim_devices') }} dd ON sb.device_category = dd.device_type
        AND 'Unknown' = dd.browser
        AND 'Unknown' = dd.os
    LEFT JOIN {{ ref('dim_ad_platform') }} dap ON LOWER(sb.traffic_source) = LOWER(dap.platform_name)
)

SELECT
    f.session_id,
    f.user_cookie_id,
    f.date_key,
    f.user_crm_id,
    f.source_key,
    apn.platform_key,
    f.medium_key,
    f.geo_key,
    f.device_key,
    f.page_views,
    f.add_to_cart_flag,
    f.bounce_flag,
    f.transaction_count,
    f.session_duration_seconds,
    f.dbt_updated_at,
    f.dbt_created_at

FROM
    fact_sessions f
LEFT JOIN {{ ref('dim_source') }} ds ON f.source_key = ds.source_key
LEFT JOIN {{ ref('dim_ad_platform') }} apn ON apn.platform_name = ds.source
