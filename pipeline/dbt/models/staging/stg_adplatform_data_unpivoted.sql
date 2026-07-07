
/*
===================================================================================
MODEL: stg_adplatform_data_unpivoted
===================================================================================

PURPOSE:
    Staging model that transforms wide-format advertising platform data into 
    normalized long format for easier analysis and aggregation across platforms.

SOURCE:
    - stg_adplatform_data (staging model with wide-format ad platform data)

BUSINESS LOGIC:
    - Unpivots 5 advertising platforms into normalized rows
    - Calculates cost-per-click (CPC) for each platform
    - Filters out zero-value records to reduce data volume
    - Maintains date grain with platform as additional dimension

GRAIN:
    One row per date per advertising platform (with activity)

PLATFORMS INCLUDED:
    - Criteo (retargeting)
    - Google (search and display)  
    - Meta/Facebook (social media)
    - RTB House (programmatic)
    - TikTok (social video)

KEY TRANSFORMATIONS:
    1. UNION ALL to combine platform data into long format
    2. CPC calculation using SAFE_DIVIDE to handle zero clicks
    3. Filtering of zero-activity records
    4. Platform name standardization

DATA QUALITY:
    - Excludes records with no impressions, clicks, or cost
    - Safe division prevents divide-by-zero errors
    - Maintains referential integrity to source data

ROW DEFINITION:
    Each row represents one day's advertising performance for a specific platform,
    with standardized metrics (impressions, clicks, cost, CPC) for cross-platform analysis.
===================================================================================
*/


WITH base_data AS (
    SELECT * FROM {{ ref('stg_adplatform_data') }}
),

unpivoted_adplatform AS (
    -- Criteo data
    SELECT 
        date,
        'criteo' as ad_platform,
        SAFE_CAST(criteo_impressions as INTEGER) as impressions,
        SAFE_CAST(criteo_clicks as INTEGER) as clicks,
        SAFE_CAST(criteo_cost as FLOAT64) as cost,
        -- Calculate CPC for this platform
        SAFE_DIVIDE(criteo_cost, criteo_clicks) as cpc,
        dbt_updated_at,
        dbt_valid_from
    FROM base_data
    WHERE criteo_impressions > 0 OR criteo_clicks > 0 OR criteo_cost > 0
    
    UNION ALL
    
    -- Google data
    SELECT 
        date,
        'google' as ad_platform,
        SAFE_CAST(google_impressions as INTEGER) as impressions,
        SAFE_CAST(google_clicks as INTEGER) as clicks,
        SAFE_CAST(google_cost as FLOAT64) as cost,
        -- Calculate CPC for this platform
        SAFE_DIVIDE(google_cost, google_clicks) as cpc,
        dbt_updated_at,
        dbt_valid_from
    FROM base_data
    WHERE google_impressions > 0 OR google_clicks > 0 OR google_cost > 0
    
    UNION ALL
    
    -- Meta data
    SELECT 
        date,
        'meta' as ad_platform,
        SAFE_CAST(meta_impressions as INTEGER) as impressions,
        SAFE_CAST(meta_clicks as INTEGER) as clicks,
        SAFE_CAST(meta_cost as FLOAT64) as cost,
        -- Calculate CPC for this platform
        SAFE_DIVIDE(meta_cost, meta_clicks) as cpc,
        dbt_updated_at,
        dbt_valid_from
    FROM base_data
    WHERE meta_impressions > 0 OR meta_clicks > 0 OR meta_cost > 0
    
    UNION ALL
    
    -- RTB House data
    SELECT 
        date,
        'rtbhouse' as ad_platform,
        SAFE_CAST(rtbhouse_impressions as INTEGER) as impressions,
        SAFE_CAST(rtbhouse_clicks as INTEGER) as clicks,
        SAFE_CAST(rtbhouse_cost as FLOAT64) as cost,
        -- Calculate CPC for this platform
        SAFE_DIVIDE(rtbhouse_cost, rtbhouse_clicks) as cpc,
        dbt_updated_at,
        dbt_valid_from
    FROM base_data
    WHERE rtbhouse_impressions > 0 OR rtbhouse_clicks > 0 OR rtbhouse_cost > 0
    
    UNION ALL
    
    -- TikTok data
    SELECT 
        date,
        'tiktok' as ad_platform,
        SAFE_CAST(tiktok_impressions as INTEGER) as impressions,
        SAFE_CAST(tiktok_clicks as INTEGER) as clicks,
        SAFE_CAST(tiktok_cost as FLOAT64) as cost,
        -- Calculate CPC for this platform
        SAFE_DIVIDE(tiktok_cost, tiktok_clicks) as cpc,
        dbt_updated_at,
        dbt_valid_from
    FROM base_data
    WHERE tiktok_impressions > 0 OR tiktok_clicks > 0 OR tiktok_cost > 0
)

SELECT 
    date,
    ad_platform,
    impressions,
    clicks,
    cost,
    cpc,
    dbt_updated_at,
    dbt_valid_from
FROM unpivoted_adplatform
ORDER BY date, ad_platform