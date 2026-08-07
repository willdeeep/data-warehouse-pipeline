{{ config(materialized='table') }}

-- Region level; parents up to dim_country. country_key is the same conformed hash dim_country stores.
SELECT
    {{ generate_int_surrogate_key(['region', 'country']) }} AS region_key,
    region AS region_name,
    {{ generate_int_surrogate_key(['country']) }} AS country_key,
    CURRENT_TIMESTAMP() AS dbt_created_at
FROM (
    SELECT DISTINCT region, country
    FROM {{ ref('int_geo_locations') }}
    WHERE region IS NOT NULL
)
