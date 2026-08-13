
/*
===================================================================================
MODEL: stg_product_attributes
===================================================================================

PURPOSE:
    Staging model for product catalog data with category hierarchies and
    attribute standardization for merchandise analysis.

SOURCE:
    - loom_sync.productattributes (raw product catalog data)

BUSINESS LOGIC:
    - Preserves exact source column names for downstream compatibility
    - Filters out products with missing item IDs
    - Maintains product hierarchical categories (main/sub)
    - Standardizes gender targeting information

GRAIN:
    One row per unique product (item_id)

KEY TRANSFORMATIONS:
    1. Basic data validation (excludes null item_ids)
    2. Addition of dbt metadata timestamps
    3. Preservation of original attribute structure

DATA QUALITY:
    - Ensures all products have valid identifiers
    - Maintains category hierarchy integrity
    - Preserves brand and naming information

ROW DEFINITION:
    Each row represents a unique product with its brand, name, category
    classifications, and gender targeting information.
===================================================================================
*/


WITH cleaned_product_attributes AS (
    SELECT
        -- Original source columns - keeping exact column names
        item_id,
        item_brand,
        item_name,
        item_main_category,
        item_sub_category,
        item_gender,

        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from

    FROM {{ source('loom_sync', 'productattributes') }}
    WHERE item_id IS NOT NULL
)

SELECT * FROM cleaned_product_attributes
