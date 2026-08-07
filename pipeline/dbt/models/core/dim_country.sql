{{ config(materialized='table') }}

-- Country level of the geographic hierarchy (snowflaked out of dim_geo).
SELECT
    {{ generate_int_surrogate_key(['country']) }} AS country_key,
    country AS country_name,
    CURRENT_TIMESTAMP() AS dbt_created_at
FROM (
    SELECT DISTINCT country
    FROM {{ ref('int_geo_locations') }}
    WHERE country IS NOT NULL
)
