
/*
===================================================================================
MODEL: stg_sessions
===================================================================================

PURPOSE:
    Staging model for user session data with traffic source standardization,
    device categorization, and session aggregation for attribution analysis.
    Ensures session_id uniqueness by aggregating duplicate sessions across dates.

SOURCE:
    - loom_sync.sessions (raw session tracking data)

BUSINESS LOGIC:
    - Standardizes traffic source values using case statements to consolidate similar sources
    - Aggregates sessions that span multiple dates into single records
    - Preserves geographic and device information using ANY_VALUE for consistency
    - Links sessions to users via cookie and CRM IDs
    - Filters out sessions without valid identifiers

GRAIN:
    One row per unique session_id (aggregated across dates if necessary)

SESSION AGGREGATION:
    - start_date: MIN(date) for sessions spanning multiple dates
    - end_date: MAX(date) for sessions spanning multiple dates
    - session_count: COUNT of original rows with the same session_id
    - Other fields: ANY_VALUE to maintain consistency

TRAFFIC SOURCE STANDARDIZATION:
    - google: consolidates google, youtube and other Google platforms
    - meta: consolidates meta, facebook variations, instagram variations
    - tiktok: consolidates tiktok, tiktok.com
    - rtbhouse: consolidates rtbhouse, tradedoubler, awin, tradedesk
    - criteo: consolidates criteo, dv360, taboola
    - Other sources: passed through unchanged (e.g., bing, yahoo, duckduckgo, sms, direct, etc.)

KEY TRANSFORMATIONS:
    1. Data type casting for user_crm_id (INTEGER)
    2. Traffic source normalization with case statements
    3. String normalization for traffic medium
    4. Session and date validation
    5. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all sessions have valid dates and session IDs
    - Safe casting prevents type conversion errors
    - Filters out empty session identifiers

ROW DEFINITION:
    Each row represents a unique session with aggregated date range, traffic attribution,
    device information, and geographic context for marketing analysis. Sessions that
    span multiple dates are consolidated with start/end dates and session count.
===================================================================================
*/


WITH cleaned_sessions AS (
    SELECT
        -- Date field
        date,
        -- Primary identifiers
        session_id,
        user_cookie_id,
        SAFE_CAST(user_crm_id AS INTEGER) as user_crm_id,
        -- Geographic information
        city,
        -- Traffic source with standardization
        CASE
            -- Google platforms (search engines)
            WHEN LOWER(TRIM(traffic_source)) IN ('google', 'youtube.com', 'youtube', 'google.com') THEN 'google'

            -- Meta/Facebook platforms
            WHEN LOWER(TRIM(traffic_source)) IN (
                'meta', 'facebook', 'facebook.com', 'l.facebook.com',
                'lm.facebook.com', 'm.facebook.com', 'instagram',
                'instagram.com', 'l.instagram.com'
            ) THEN 'meta'

            -- TikTok platforms
            WHEN LOWER(TRIM(traffic_source)) IN ('tiktok', 'tiktok.com') THEN 'tiktok'

            -- RTB House and affiliate/programmatic platforms
            WHEN LOWER(TRIM(traffic_source)) IN ('rtbhouse', 'tradedoubler', 'awin', 'tradedesk') THEN 'rtbhouse'

            -- Criteo and other programmatic/retargeting platforms
            WHEN LOWER(TRIM(traffic_source)) IN ('criteo', 'dv360', 'taboola') THEN 'criteo'

            WHEN LOWER(TRIM(traffic_source)) IN ('twitter', 'twitter.com') THEN 'twitter'

            -- Pass through all other traffic sources unchanged
            ELSE SAFE_CAST(traffic_source AS STRING)
        END AS traffic_source,
        -- Traffic medium safe casting
        SAFE_CAST(traffic_medium AS STRING) as traffic_medium,
        -- Device category
        device_category,
        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from
    FROM {{ source('loom_sync', 'sessions') }}
    WHERE date IS NOT NULL
      AND session_id IS NOT NULL
      AND TRIM(session_id) != ''
),

aggregated_sessions AS (
    SELECT
        -- Primary identifiers
        session_id,

        -- Date aggregation: min as start_date, max as end_date
        MIN(date) AS start_date,
        MAX(date) AS end_date,

        -- Session count: count of rows with the same session_id
        COUNT(*) AS session_count,

        -- Take first non-null values for other fields (or most recent)
        ANY_VALUE(user_cookie_id) AS user_cookie_id,
        ANY_VALUE(user_crm_id) AS user_crm_id,
        ANY_VALUE(city) AS city,
        ANY_VALUE(traffic_source) AS traffic_source,
        ANY_VALUE(traffic_medium) AS traffic_medium,
        ANY_VALUE(device_category) AS device_category,

        -- Metadata - use max timestamps to get most recent
        MAX(dbt_updated_at) AS dbt_updated_at,
        MIN(dbt_valid_from) AS dbt_valid_from

    FROM cleaned_sessions
    GROUP BY session_id
)

SELECT * FROM aggregated_sessions
