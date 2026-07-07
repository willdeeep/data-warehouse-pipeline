
/*
===================================================================================
MODEL: stg_product_returns
===================================================================================

PURPOSE:
    Staging model for product return data used in return rate analysis and 
    customer satisfaction metrics.

SOURCE:
    - loom_sync.product_returns (raw product return transactions)

BUSINESS LOGIC:
    - Converts quantities to appropriate data types (INTEGER for items, FLOAT64 for returns)
    - Filters out records with missing return dates
    - Maintains return transaction details for analysis
    - Supports return rate and refund calculations

GRAIN:
    One row per return transaction line item

KEY TRANSFORMATIONS:
    1. Data type casting for quantity fields
    2. Date validation (excludes null return dates)
    3. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all returns have valid dates
    - Safe casting prevents type conversion errors
    - Maintains transaction integrity for return analysis

ROW DEFINITION:
    Each row represents a specific item return within a transaction,
    including original quantity, return quantity, and processing status.
===================================================================================
*/


WITH cleaned_product_returns AS (
    SELECT
        -- Original source columns with SAFE_CAST for data types
        return_date,
        SAFE_CAST(transaction_id AS INTEGER) as transaction_id,
        SAFE_CAST(item_id as INTEGER) as product_id,  -- Normalize to product_id
        SAFE_CAST(item_quantity as INTEGER) as product_quantity,  -- Normalize to product_quantity
        SAFE_CAST(return_quantity as FLOAT64) as return_quantity,
        return_status,
        
        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from
        
    FROM {{ source('loom_sync', 'product_returns') }}
    WHERE return_date IS NOT NULL
)

SELECT * FROM cleaned_product_returns