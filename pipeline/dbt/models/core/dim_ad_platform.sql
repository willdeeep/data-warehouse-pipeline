/*
===================================================================================
MODEL: dim_ad_platform
===================================================================================

PURPOSE:
    Advertising platform dimension table for marketing spend analysis.
    Standardizes ad platform classifications and channel types.

SOURCE:
    - {{ ref('stg_adplatform_data_unpivoted') }}

GRAIN:
    One row per unique advertising platform

KEY ATTRIBUTES:
    - Platform identification and naming
    - Channel type categorization (Paid Social, Search, DSP, etc.)
    - Marketing medium classification
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['platform_key'], 'type': 'btree'},
        {'columns': ['platform_name'], 'type': 'btree'},
        {'columns': ['channel_type'], 'type': 'btree'}
    ]
) }}

WITH platform_data AS (
    SELECT DISTINCT
        ad_platform AS platform_name,
        MIN(dbt_valid_from) AS first_seen_at,
        MAX(dbt_updated_at) AS last_seen_at
    FROM {{ ref('stg_adplatform_data_unpivoted') }}
    WHERE ad_platform IS NOT NULL
    GROUP BY 1
),

platform_dimension AS (
    SELECT
        -- Primary key
        {{ generate_int_surrogate_key(['platform_name']) }} AS platform_key,
        
        platform_name,
        
        -- Classify channel type based on platform
        CASE 
            WHEN LOWER(platform_name) IN ('google ads', 'bing ads', 'yahoo ads') THEN 'Search'
            WHEN LOWER(platform_name) IN ('facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'snapchat', 'pinterest') THEN 'Paid Social'
            WHEN LOWER(platform_name) IN ('google display', 'programmatic', 'dsp', 'demand side platform') THEN 'DSP'
            WHEN LOWER(platform_name) IN ('youtube', 'video', 'connected tv', 'ctv') THEN 'Video'
            WHEN LOWER(platform_name) IN ('amazon', 'walmart', 'marketplace') THEN 'Retail Media'
            WHEN LOWER(platform_name) IN ('email', 'newsletter') THEN 'Email'
            ELSE 'Other'
        END AS channel_type,
        
        -- dbt metadata
        last_seen_at AS dbt_updated_at,
        first_seen_at AS dbt_created_at
        
    FROM platform_data
)

SELECT * FROM platform_dimension
