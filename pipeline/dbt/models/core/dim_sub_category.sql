{{ config(materialized='table') }}

-- Sub level of the product category hierarchy; parents up to dim_main_category.
SELECT
    {{ generate_int_surrogate_key(['item_sub_category']) }} AS sub_category_key,
    item_sub_category AS sub_category_name,
    {{ generate_int_surrogate_key(['item_main_category']) }} AS main_category_key,
    CURRENT_TIMESTAMP() AS dbt_created_at
FROM (
    SELECT DISTINCT item_sub_category, item_main_category
    FROM {{ ref('stg_product_attributes') }}
    WHERE item_sub_category IS NOT NULL
)
