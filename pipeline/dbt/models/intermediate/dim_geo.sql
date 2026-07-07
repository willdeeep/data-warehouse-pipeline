/*
===================================================================================
MODEL: dim_geo
===================================================================================

PURPOSE:
    Geographic dimension table for location-based analysis.
    Provides standardized geography hierarchy for user and session analysis.

SOURCE:
    - {{ ref('stg_sessions') }}
    - {{ ref('stg_users') }}

GRAIN:
    One row per unique geographic location

KEY ATTRIBUTES:
    - Geographic hierarchy (city, region, country)
    - Standardized location names
    - Default country assignment
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['geo_key'], 'type': 'btree'},
        {'columns': ['city'], 'type': 'btree'},
        {'columns': ['country'], 'type': 'btree'}
    ]
) }}

WITH geo_from_sessions AS (
    SELECT DISTINCT
        city,
        -- Extract region from city if available (simplified logic)
        CASE 
            WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(1)])
            ELSE NULL 
        END AS region,
        'US' AS country,  -- Default as specified in schema
        CURRENT_TIMESTAMP AS first_seen_at,
        CURRENT_TIMESTAMP AS last_seen_at
    FROM {{ ref('stg_sessions') }}
    WHERE city IS NOT NULL 
      AND TRIM(city) != ''
    GROUP BY 1, 2, 3
),

geo_from_users AS (
    SELECT DISTINCT
        city,
        -- Extract region from city if available (simplified logic)
        CASE 
            WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(1)])
            ELSE NULL 
        END AS region,
        'US' AS country,  -- Default as specified in schema
        CURRENT_TIMESTAMP AS first_seen_at,
        CURRENT_TIMESTAMP AS last_seen_at
    FROM {{ ref('stg_users') }}
    WHERE city IS NOT NULL 
      AND TRIM(city) != ''
    GROUP BY 1, 2, 3
),

geo_combined AS (
    SELECT 
        COALESCE(s.city, u.city) AS city,
        COALESCE(s.region, u.region) AS region,
        COALESCE(s.country, u.country) AS country,
        LEAST(
            COALESCE(s.first_seen_at, u.first_seen_at),
            COALESCE(u.first_seen_at, s.first_seen_at)
        ) AS first_seen_at,
        GREATEST(
            COALESCE(s.last_seen_at, u.last_seen_at),
            COALESCE(u.last_seen_at, s.last_seen_at)
        ) AS last_seen_at
    FROM geo_from_sessions s
    FULL OUTER JOIN geo_from_users u 
        ON s.city = u.city AND s.country = u.country
),

geo_dimension AS (
    SELECT
        -- Primary key: simple integer ID
        ROW_NUMBER() OVER (ORDER BY country, region, city) AS geo_key,
        
        -- Clean city name (remove region suffix if present)
        CASE 
            WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(0)])
            ELSE city 
        END AS city,
        region,
        country,
        
        -- dbt metadata
        last_seen_at AS dbt_updated_at,
        first_seen_at AS dbt_created_at
        
    FROM geo_combined
    WHERE city IS NOT NULL
)

SELECT * FROM geo_dimension
