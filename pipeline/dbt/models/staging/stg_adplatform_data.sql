
/*
===================================================================================
MODEL: stg_adplatform_data
===================================================================================

PURPOSE:
    Staging model for advertising platform performance data in wide format,
    standardizing metrics across multiple ad platforms for performance analysis.

SOURCE:
    - loom_sync.adplatform_data (raw advertising platform metrics)

BUSINESS LOGIC:
    - Preserves wide format with separate columns for each platform
    - Converts impression and click counts to INTEGER
    - Converts cost metrics to FLOAT64 for financial calculations
    - Maintains daily grain for time-series analysis

GRAIN:
    One row per date with metrics for all advertising platforms

PLATFORMS INCLUDED:
    - Criteo (retargeting)
    - Google (search and display)
    - Meta/Facebook (social media)
    - RTB House (programmatic)
    - TikTok (social video)

KEY TRANSFORMATIONS:
    1. Data type casting for all numeric metrics
    2. Date validation (excludes null dates)
    3. Consistent naming across platforms
    4. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all records have valid dates
    - Safe casting prevents type conversion errors
    - Maintains platform-specific data integrity

ROW DEFINITION:
    Each row represents one day's advertising performance across all platforms,
    with impressions, clicks, and cost data for each advertising channel.
===================================================================================
*/

WITH cleaned_adplatform AS (
    SELECT 
        -- Original source columns with SAFE_CAST for data types
        date,
        SAFE_CAST(criteo_impressions as INTEGER) as criteo_impressions,
        SAFE_CAST(criteo_clicks as INTEGER) as criteo_clicks,
        SAFE_CAST(criteo_cost as FLOAT64) as criteo_cost,
        SAFE_CAST(google_impressions as INTEGER) as google_impressions,
        SAFE_CAST(google_clicks as INTEGER) as google_clicks,
        SAFE_CAST(google_cost as FLOAT64) as google_cost,
        SAFE_CAST(meta_impressions as INTEGER) as meta_impressions,
        SAFE_CAST(meta_clicks as INTEGER) as meta_clicks,
        SAFE_CAST(meta_cost as FLOAT64) as meta_cost,
        SAFE_CAST(rtbhouse_impressions as INTEGER) as rtbhouse_impressions,
        SAFE_CAST(rtbhouse_clicks as INTEGER) as rtbhouse_clicks,
        SAFE_CAST(rtbhouse_cost as FLOAT64) as rtbhouse_cost,
        SAFE_CAST(tiktok_impressions as INTEGER) as tiktok_impressions,
        SAFE_CAST(tiktok_clicks as INTEGER) as tiktok_clicks,
        SAFE_CAST(tiktok_cost as FLOAT64) as tiktok_cost,
        
        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from
        
    FROM {{ source('loom_sync', 'adplatform_data') }}
    WHERE date IS NOT NULL
)

SELECT * FROM cleaned_adplatform
