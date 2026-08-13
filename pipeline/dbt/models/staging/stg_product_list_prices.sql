
/*
===================================================================================
MODEL: stg_product_list_prices
===================================================================================

PURPOSE:
    Staging model for product list prices used in discount analysis and
    revenue calculations.

SOURCE:
    - loom_sync.product_listprices (raw product pricing data)

BUSINESS LOGIC:
    - Converts price values to FLOAT64 for financial calculations
    - Filters out records with missing or empty product IDs
    - Normalizes item_id to product_id for consistent naming
    - Maintains official pricing for discount and margin analysis
    - Supports pricing strategy and competitive analysis

GRAIN:
    One row per product with list price information

KEY TRANSFORMATIONS:
    1. Data type casting for list_price (FLOAT64)
    2. Column name normalization from item_* to product_*
    3. Data validation (excludes null/empty product IDs)
    4. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all records have valid product identifiers
    - Safe casting prevents type conversion errors
    - Maintains pricing integrity for revenue calculations

ROW DEFINITION:
    Each row represents a product's official list price used for calculating
    discounts, margins, and pricing analytics.
===================================================================================
*/


WITH cleaned_product_list_prices AS (
    SELECT
        -- Primary key
        SAFE_CAST(item_id as INTEGER) as product_id,  -- Normalize to product_id

        -- List price validation and cleaning
        SAFE_CAST(item_list_price as FLOAT64) as list_price,  -- Normalize to list_price

        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from

    FROM {{ source('loom_sync', 'product_listprices') }}
    WHERE item_id IS NOT NULL
      AND TRIM(item_id) != ''
)

SELECT * FROM cleaned_product_list_prices
