
/*
===================================================================================
MODEL: stg_transactions
===================================================================================

PURPOSE:
    Staging model for transaction header data with data type standardization
    and basic validation.

SOURCE:
    - loom_sync.transactions (raw transaction data)

BUSINESS LOGIC:
    - Converts monetary fields to FLOAT64 using SAFE_CAST
    - Preserves all original source columns with proper typing
    - Filters out records with missing transaction dates
    - Adds dbt processing metadata

GRAIN:
    One row per transaction

KEY TRANSFORMATIONS:
    1. Data type casting for monetary fields (revenue, shipping, total)
    2. Date validation (excludes null dates)
    3. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all transactions have valid dates
    - Safe casting prevents type conversion errors
    - Preserves data integrity from source

ROW DEFINITION:
    Each row represents a single transaction header with customer identifiers,
    session context, monetary amounts, and coupon information.
===================================================================================
*/


WITH cleaned_transactions AS (
    SELECT
        -- Original source columns with SAFE_CAST for data types
        date,
        user_cookie_id,
        -- Clean and cast user_crm_id with better handling
        CASE
            WHEN user_crm_id IS NULL OR TRIM(user_crm_id) = '' THEN NULL
            WHEN REGEXP_CONTAINS(TRIM(user_crm_id), r'^[0-9]+$') THEN SAFE_CAST(user_crm_id AS INTEGER)
            ELSE NULL  -- Invalid non-numeric values become NULL
        END as user_crm_id,
        session_id,
        SAFE_CAST(transaction_id AS INTEGER) as transaction_id,
        transaction_coupon,
        SAFE_CAST(transaction_revenue as FLOAT64) as transaction_revenue,
        SAFE_CAST(transaction_shipping as FLOAT64) as transaction_shipping,
        SAFE_CAST(transaction_total as FLOAT64) as transaction_total,

        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from

    FROM {{ source('loom_sync', 'transactions') }}
    WHERE date IS NOT NULL
)

SELECT * FROM cleaned_transactions
