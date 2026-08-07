{{ config(materialized='ephemeral') }}

-- Shared geo derivation lifted from the original dim_geo so dim_country / dim_region / dim_geo
-- share one definition. Ephemeral: compiles into its consumers, creates no table.
WITH geo_from_sessions AS (
    SELECT DISTINCT
        CASE WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(0)]) ELSE city END AS city,
        CASE WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(1)]) ELSE NULL END AS region,
        'US' AS country
    FROM {{ ref('stg_sessions') }}
    WHERE city IS NOT NULL AND TRIM(city) != ''
),

geo_from_users AS (
    SELECT DISTINCT
        CASE WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(0)]) ELSE city END AS city,
        CASE WHEN city LIKE '%,%' THEN TRIM(SPLIT(city, ',')[SAFE_OFFSET(1)]) ELSE NULL END AS region,
        'US' AS country
    FROM {{ ref('stg_users') }}
    WHERE city IS NOT NULL AND TRIM(city) != ''
)

SELECT DISTINCT city, region, country
FROM (
    SELECT * FROM geo_from_sessions
    UNION DISTINCT
    SELECT * FROM geo_from_users
)
