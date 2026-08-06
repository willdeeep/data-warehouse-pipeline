{{ config(materialized='table') }}

-- Top level of the product category hierarchy.
SELECT
    {{ dbt_utils.generate_surrogate_key(['item_main_category']) }} AS main_category_key,
    item_main_category AS main_category_name,
    CURRENT_TIMESTAMP() AS dbt_created_at
FROM (
    SELECT DISTINCT item_main_category
    FROM {{ ref('stg_product_attributes') }}
    WHERE item_main_category IS NOT NULL
)
