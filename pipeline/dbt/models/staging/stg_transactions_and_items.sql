
/*
===================================================================================
MODEL: stg_transactions_and_items
===================================================================================

PURPOSE:
    Staging model for transaction line item data with proper data type casting
    and validation for product-level purchase details.

SOURCE:
    - loom_sync.transactionsanditems (raw transaction line item data)

BUSINESS LOGIC:
    - Converts item_price to product_price (FLOAT64) for monetary calculations
    - Converts item_quantity to product_quantity (INTEGER) for inventory counts
    - Normalizes item_id to product_id for consistent naming
    - Preserves transaction and product identifiers
    - Filters out records with missing dates

GRAIN:
    One row per transaction line item (transaction_id + product_id combination)

KEY TRANSFORMATIONS:
    1. Data type casting for price (FLOAT64) and quantity (INTEGER)
    2. Column name normalization from item_* to product_*
    3. Date validation (excludes null dates)
    4. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all line items have valid transaction dates
    - Safe casting prevents type conversion errors
    - Maintains referential integrity to transactions

ROW DEFINITION:
    Each row represents a single product line item within a transaction,
    including the specific product purchased, its price, and quantity.
===================================================================================
*/


WITH cleaned_transaction_items AS (
    SELECT
        -- Original source columns with SAFE_CAST for data types
        date,
        SAFE_CAST(item_id as INTEGER) as item_id,              -- unique per-unit grain key
        SAFE_CAST(transaction_id AS INTEGER) as transaction_id,
        SAFE_CAST(product_id as INTEGER) as product_id,        -- product SKU
        ROUND(SAFE_CAST(item_price as FLOAT64), 2) as product_price,  -- Normalize to product_price
        SAFE_CAST(item_quantity as INTEGER) as product_quantity,  -- always 1 (one unit per row)

        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from

    FROM {{ source('loom_sync', 'transactionsanditems') }}
    WHERE date IS NOT NULL
)

SELECT * FROM cleaned_transaction_items
