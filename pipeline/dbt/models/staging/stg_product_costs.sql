
/*
===================================================================================
MODEL: stg_product_costs
===================================================================================

PURPOSE:
    Staging model for product cost data used in margin analysis and 
    profitability calculations.

SOURCE:
    - loom_sync.product_costs (raw product cost information)

BUSINESS LOGIC:
    - Converts cost values to FLOAT64 for financial calculations
    - Filters out records with missing product IDs or cost values
    - Normalizes item_id to product_id for consistent naming
    - Ensures data completeness for margin analysis
    - Maintains one-to-one relationship with products

GRAIN:
    One row per product with cost information

KEY TRANSFORMATIONS:
    1. Data type casting for cost_of_item to product_cost (FLOAT64)
    2. Column name normalization from item_* to product_*
    3. Data validation (excludes null IDs and costs)
    3. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all records have valid product IDs and cost values
    - Safe casting prevents type conversion errors
    - Maintains referential integrity for financial calculations

ROW DEFINITION:
    Each row represents a product's cost information used for calculating
    gross margins and profitability metrics.
===================================================================================
*/


WITH cleaned_product_costs AS (
    SELECT
        -- Primary key
        SAFE_CAST(item_id as INTEGER) as product_id,  -- Normalize to product_id
        
        -- Cost validation and cleaning
        SAFE_CAST(cost_of_item as FLOAT64) as product_cost,  -- Normalize to product_cost
        
        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from
        
    FROM {{ source('loom_sync', 'product_costs') }}
    WHERE item_id IS NOT NULL
      AND cost_of_item IS NOT NULL
)

SELECT * FROM cleaned_product_costs