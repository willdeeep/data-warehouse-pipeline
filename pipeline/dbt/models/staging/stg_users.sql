{{ config(materialized='table') }}

WITH user_transactions AS (
    SELECT
        SAFE_CAST(user_crm_id AS INTEGER) as user_crm_id,
        COUNT(DISTINCT transaction_id) as transaction_count,
        SUM(transaction_total) as total_revenue
    FROM {{source('loom_sync','transactions')}}
    GROUP BY user_crm_id
),

base_users AS (
    SELECT
        SAFE_CAST(user_crm_id AS INTEGER) as user_crm_id,
        city,
        user_gender,
        SAFE_CAST(registration_date AS date) AS registration_date,
        SAFE_CAST(latest_login_date AS date) AS latest_login_date,
        SAFE_CAST(first_purchase_date AS date) AS first_purchase_date,
        SAFE_CAST(latest_purchase_date AS date) AS latest_purchase_date,
        SAFE_CAST(valid_from AS date) AS valid_from,
        opt_in_status,
        loom_plus_status,
        loom_plus_tier,
        -- Add metadata for SCD tracking
        CURRENT_TIMESTAMP() AS dbt_updated_at,
        CURRENT_TIMESTAMP() AS dbt_valid_from
    FROM {{source('loom_sync','users')}}
    -- Integer contract: keep only rows whose user_crm_id is integer-castable. The old
    -- `LENGTH(...) = 7` guard silently dropped valid ids and is removed (#36); a not_null test on
    -- user_crm_id guards the key instead.
    WHERE SAFE_CAST(user_crm_id AS INT64) IS NOT NULL
)

SELECT
    u.*,
    COALESCE(t.transaction_count, 0) as transaction_count,
    COALESCE(t.total_revenue, 0.0) as total_revenue
FROM base_users u
LEFT JOIN user_transactions t ON u.user_crm_id = t.user_crm_id
