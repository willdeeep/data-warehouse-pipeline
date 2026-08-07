{{ config(
    materialized='table',
    indexes=[
        {'columns': ['geo_key'], 'type': 'btree'},
        {'columns': ['city'], 'type': 'btree'},
        {'columns': ['region_key'], 'type': 'btree'}
    ]
) }}

/*
===================================================================================
MODEL: dim_geo
===================================================================================
City (leaf) level of the geographic hierarchy. Parents up to dim_region via region_key.
region_key is NULL where no region was parsed from the city string (thin-data caveat:
Faker cities rarely carry a ", region" suffix, so most rows have a NULL region_key).
The city/region/country split is shared with dim_region/dim_country via int_geo_locations.
===================================================================================
*/

WITH geo AS (
    SELECT DISTINCT city, region, country
    FROM {{ ref('int_geo_locations') }}
    WHERE city IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY country, region, city) AS geo_key,
    city,
    CASE
        WHEN region IS NOT NULL THEN {{ generate_int_surrogate_key(['region', 'country']) }}
        ELSE NULL
    END AS region_key,
    CURRENT_TIMESTAMP() AS dbt_updated_at,
    CURRENT_TIMESTAMP() AS dbt_created_at
FROM geo
