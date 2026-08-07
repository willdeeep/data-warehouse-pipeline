{{ config(materialized='table') }}

-- Brand dimension (snowflaked out of dim_products).
SELECT
    {{ generate_int_surrogate_key(['item_brand']) }} AS brand_key,
    item_brand AS brand_name,
    CURRENT_TIMESTAMP() AS dbt_created_at
FROM (
    SELECT DISTINCT item_brand
    FROM {{ ref('stg_product_attributes') }}
    WHERE item_brand IS NOT NULL
)
