/*
===================================================================================
FACT: fct_transactions
===================================================================================

PURPOSE:
    Fact table for transaction line items with comprehensive business metrics
    and foreign key relationships to dimension tables.

GRAIN:
    One row per transaction/product line item (transaction_id + item_id combination)

KEY BUSINESS METRICS:
    - Item-level revenue, price, and quantity
    - Transaction-level totals (revenue, shipping, total)
    - Calculated profit margin and item contribution
    - Customer and session context
    - Return status from staging stg_product_returns

FOREIGN KEYS:
    - date_key -> dim_date
    - user_crm_id -> dim_users  
    - product_id -> dim_products
    - session_id -> fct_sessions

===================================================================================
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['date_key'], 'type': 'btree'},
        {'columns': ['user_crm_id'], 'type': 'btree'},
        {'columns': ['product_id'], 'type': 'btree'},
        {'columns': ['transaction_id'], 'type': 'btree'}
    ]
) }}

WITH transaction_items AS (
    SELECT
        -- Primary Keys
        CONCAT(CAST(transaction_id AS STRING), '.', CAST(product_id AS STRING)) as transaction_product_id,
        transaction_id,
        product_id,
        
        -- Date Key - formatted as a string 'YYYYMMDD' for efficient querying
        CAST(REPLACE(CAST(date AS STRING), '-', '') AS INT64) as date_key,
        
        -- Product Metrics
        product_price,
        product_quantity,
        ROUND(product_price * product_quantity, 2) as product_revenue,
        
        -- Source metadata
        date,
        dbt_updated_at,
        dbt_valid_from
        
    FROM {{ ref('stg_transactions_and_items') }}
),

transactions AS (
    SELECT
        transaction_id,
        user_cookie_id,
        user_crm_id,
        session_id,
        transaction_coupon,
        transaction_revenue,
        transaction_shipping,
        transaction_total
        
    FROM {{ ref('stg_transactions') }}
),

product_returns AS (
    SELECT
        transaction_id,
        product_id,
        return_status,
        return_quantity,
        CAST(REPLACE(CAST(return_date AS STRING), '-', '') AS INT64) as return_date
        
    FROM {{ ref('stg_product_returns') }}
),

purchase_time AS (  
    SELECT 
        -- Extract purchase event times for session context
        transaction_id,
        item_id as product_id,
        event_time
    FROM {{ ref('stg_funnel_events') }}
),
final AS (
    SELECT
        -- Primary Key
        DISTINCT ti.transaction_product_id,
        
        -- Foreign Keys
        ti.date_key,
        COALESCE(t.user_crm_id, NULL) as user_crm_id,  -- Natural key for user dimension
        COALESCE(t.user_cookie_id, NULL) as user_cookie_id,  -- Anonymous user identifier
        ti.product_id as product_id,  -- Natural key for product dimension
        
        -- Natural Keys
        ti.transaction_id,
        EXTRACT(TIME FROM pt.event_time) as purchase_time,  -- Timestamp of the purchase event
        t.session_id,
        
        -- Product Metrics
        ti.product_price,
        ti.product_quantity,
        ti.product_revenue,
        
        -- Transaction Context
        t.transaction_revenue,
        t.transaction_shipping,
        t.transaction_total,
        t.transaction_coupon,
        
        -- Calculated Business Metrics
        ROUND(ti.product_revenue / NULLIF(t.transaction_total, 0) * 100, 2) as product_contribution_pct,
        CASE 
            WHEN t.transaction_coupon IS NOT NULL THEN 'Discount'
            ELSE 'Full Price'
        END as pricing_type,
        
        -- Customer Classification
        CASE 
            WHEN t.user_crm_id IS NOT NULL THEN 'Registered'
            ELSE 'Guest'
        END as customer_type,

        -- Loom+ Status (pass through from stg_users, null for empty/null values)
        CASE 
            WHEN u.loom_plus_status IS NOT NULL AND u.loom_plus_status = TRUE 
            THEN CAST(u.loom_plus_status AS STRING)
            ELSE NULL
        END as loom_plus_status,

        -- Return Information
        pr.return_status,
        pr.return_quantity,
        pr.return_date,
        
        -- Return Calculations (matching YAML definition)
        CASE 
            WHEN pr.return_status IS NOT NULL THEN TRUE
            ELSE FALSE
        END as has_return,
        
        CASE 
            WHEN ti.product_quantity > 0 THEN 
                ROUND(COALESCE(pr.return_quantity, 0) / ti.product_quantity * 100, 2)
            ELSE 0
        END as return_rate_pct,

        
        -- Metadata
        ti.dbt_updated_at,
        ti.dbt_valid_from
        
    FROM transaction_items ti
    LEFT JOIN transactions t
        ON ti.transaction_id = t.transaction_id
    LEFT JOIN {{ ref('stg_users') }} u
        ON t.user_crm_id = u.user_crm_id
    LEFT JOIN product_returns pr
        ON ti.transaction_id = pr.transaction_id
        AND ti.product_id = pr.product_id
    LEFT JOIN purchase_time pt
        ON ti.product_id = pt.product_id AND t.transaction_id = pt.transaction_id
)

SELECT * FROM final