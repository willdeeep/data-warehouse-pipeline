/*
===================================================================================
MART: rpt_customer_activity
===================================================================================

PURPOSE:
    Comprehensive customer activity tracking mart leveraging SCD Type 2 user
    dimensions to provide historical customer journey analysis.

GRAIN:
    One row per customer activity event (transactions, profile changes)

SOURCES:
    - dim_users (SCD Type 2 for historical customer profiles)
    - fct_transactions (transaction events)
    - dim_products (for product context)
    - dim_date (for temporal analysis)

KEY FEATURES:
    - Customer journey tracking across time
    - Profile change events and transitions
    - Transaction activity with customer context at time of purchase
    - Cohort and lifecycle analysis capabilities

BUSINESS VALUE:
    - Track customer evolution over time
    - Analyze impact of profile changes on behavior
    - Customer lifecycle and retention analysis
    - Loom+ tier transition analysis
    - Historical customer segmentation
===================================================================================
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['user_crm_id'], 'type': 'btree'},
        {'columns': ['activity_date'], 'type': 'btree'},
        {'columns': ['activity_type'], 'type': 'btree'},
        {'columns': ['customer_state_at_time'], 'type': 'btree'}
    ]
) }}

WITH customer_profile_changes AS (
    -- Track customer profile change events from SCD history
    SELECT
        user_crm_id,
        'profile_change' AS activity_type,
        CAST(valid_from AS DATE) AS activity_date,
        DATETIME(CAST(valid_from AS DATE), TIME '12:00:00') AS activity_timestamp,

        -- Customer state at this point in time
        city AS customer_city,
        gender AS customer_gender,
        loom_plus_status,
        loom_plus_tier,
        opt_in_status,
        lifetime_orders,
        lifetime_value,

        -- Change indicators
        LAG(city) OVER (PARTITION BY user_crm_id ORDER BY valid_from) AS prev_city,
        LAG(loom_plus_status) OVER (PARTITION BY user_crm_id ORDER BY valid_from) AS prev_loom_plus_status,
        LAG(loom_plus_tier) OVER (PARTITION BY user_crm_id ORDER BY valid_from) AS prev_loom_plus_tier,
        LAG(lifetime_value) OVER (PARTITION BY user_crm_id ORDER BY valid_from) AS prev_lifetime_value,

        -- Event metadata (standardized types)
        CAST(NULL AS INT64) AS transaction_id,
        CAST(NULL AS INT64) AS product_id,
        CAST(NULL AS FLOAT64) AS product_revenue,
        CAST(NULL AS INT64) AS product_quantity,

        -- Customer segmentation at time of event
        CASE
            WHEN loom_plus_status = TRUE THEN 'Premium Customer'
            WHEN lifetime_orders >= 5 THEN 'Loyal Customer'
            WHEN lifetime_orders >= 2 THEN 'Repeat Customer'
            ELSE 'New Customer'
        END AS customer_state_at_time,

        user_surrogate_key AS customer_version_key

    FROM {{ ref('dim_users') }}
    WHERE user_crm_id IS NOT NULL
),

transaction_activity AS (
    -- Track transaction events with customer state at time of purchase
    SELECT
        ft.user_crm_id AS user_crm_id,
        'transaction' AS activity_type,
        PARSE_DATE('%Y%m%d', CAST(ft.date_key AS STRING)) AS activity_date,
        DATETIME(PARSE_DATE('%Y%m%d', CAST(ft.date_key AS STRING)), TIME '12:00:00') AS activity_timestamp,

        -- Customer state at time of transaction (point-in-time join)
        u.city AS customer_city,
        u.gender AS customer_gender,
        u.loom_plus_status,
        u.loom_plus_tier,
        u.opt_in_status,
        u.lifetime_orders,
        u.lifetime_value,

        -- Previous state for change tracking (NULL for transactions)
        CAST(NULL AS STRING) AS prev_city,
        CAST(NULL AS BOOLEAN) AS prev_loom_plus_status,
        CAST(NULL AS STRING) AS prev_loom_plus_tier,
        CAST(NULL AS FLOAT64) AS prev_lifetime_value,

        -- Transaction details
        CAST(ft.transaction_id AS INT64) AS transaction_id,
        ft.product_id AS product_id,
        ft.product_revenue,
        ft.product_quantity,

        -- Customer segmentation at time of transaction
        CASE
            WHEN u.loom_plus_status = TRUE THEN 'Premium Customer'
            WHEN u.lifetime_orders >= 5 THEN 'Loyal Customer'
            WHEN u.lifetime_orders >= 2 THEN 'Repeat Customer'
            ELSE 'New Customer'
        END AS customer_state_at_time,

        u.user_surrogate_key AS customer_version_key

    FROM {{ ref('fct_transactions') }} ft
    -- Point-in-time join to get customer state at transaction date
    INNER JOIN {{ ref('dim_users') }} u ON ft.user_crm_id = u.user_crm_id
        AND PARSE_DATE('%Y%m%d', CAST(ft.date_key AS STRING)) >= CAST(u.valid_from AS DATE)
        AND (u.valid_to IS NULL OR PARSE_DATE('%Y%m%d', CAST(ft.date_key AS STRING)) < CAST(u.valid_to AS DATE))
    WHERE ft.user_crm_id IS NOT NULL
),

customer_activity_consolidated AS (
    SELECT
        user_crm_id,
        activity_type,
        activity_date,
        activity_timestamp,
        customer_city,
        customer_gender,
        loom_plus_status,
        loom_plus_tier,
        opt_in_status,
        lifetime_orders,
        lifetime_value,
        prev_city,
        prev_loom_plus_status,
        prev_loom_plus_tier,
        prev_lifetime_value,
        transaction_id,
        product_id,
        product_revenue,
        product_quantity,
        customer_state_at_time,
        customer_version_key,

        -- Change type classification
        CASE
            WHEN activity_type = 'profile_change' AND prev_city IS NOT NULL AND prev_city != customer_city
                THEN 'Location Change'
            WHEN activity_type = 'profile_change' AND prev_loom_plus_status IS NOT NULL AND prev_loom_plus_status != loom_plus_status
                THEN 'Loom+ Status Change'
            WHEN activity_type = 'profile_change' AND prev_loom_plus_tier IS NOT NULL AND prev_loom_plus_tier != loom_plus_tier
                THEN 'Loom+ Tier Change'
            WHEN activity_type = 'profile_change' AND prev_lifetime_value IS NOT NULL AND lifetime_value > prev_lifetime_value
                THEN 'Value Increase'
            WHEN activity_type = 'transaction' THEN 'Purchase'
            ELSE 'Other Change'
        END AS change_type

    FROM customer_profile_changes
    WHERE activity_type = 'profile_change' AND (
        prev_city IS NOT NULL OR
        prev_loom_plus_status IS NOT NULL OR
        prev_loom_plus_tier IS NOT NULL OR
        prev_lifetime_value IS NOT NULL
    )  -- Only show actual changes, not initial records

    UNION ALL

    SELECT
        user_crm_id,
        activity_type,
        activity_date,
        activity_timestamp,
        customer_city,
        customer_gender,
        loom_plus_status,
        loom_plus_tier,
        opt_in_status,
        lifetime_orders,
        lifetime_value,
        prev_city,
        prev_loom_plus_status,
        prev_loom_plus_tier,
        prev_lifetime_value,
        transaction_id,
        product_id,
        product_revenue,
        product_quantity,
        customer_state_at_time,
        customer_version_key,
        'Purchase' AS change_type
    FROM transaction_activity
),

final_mart AS (
    SELECT
        ca.*,

        -- Add date dimension context
        d.year AS activity_year,
        d.quarter AS activity_quarter,
        d.month AS activity_month,
        d.day_of_week AS activity_day_of_week,
        d.is_weekend AS activity_is_weekend,

        -- Add product context for transactions
        b.brand_name AS product_brand,
        mc.main_category_name AS product_category,
        p.list_price AS product_list_price,

        -- Customer journey metrics
        ROW_NUMBER() OVER (PARTITION BY ca.user_crm_id ORDER BY ca.activity_timestamp) AS customer_activity_sequence,

        -- Time since last activity
        LAG(ca.activity_date) OVER (PARTITION BY ca.user_crm_id ORDER BY ca.activity_timestamp) AS prev_activity_date,
        DATE_DIFF(ca.activity_date, LAG(ca.activity_date) OVER (PARTITION BY ca.user_crm_id ORDER BY ca.activity_timestamp), DAY) AS days_since_last_activity,

        -- Customer tenure at time of activity
        DATE_DIFF(ca.activity_date,
            FIRST_VALUE(ca.activity_date) OVER (PARTITION BY ca.user_crm_id ORDER BY ca.activity_timestamp),
            DAY) AS customer_tenure_days,

        -- Current timestamp for analysis
        CURRENT_TIMESTAMP() AS mart_updated_at

    FROM customer_activity_consolidated ca
    LEFT JOIN {{ ref('dim_date') }} d ON ca.activity_date = d.date
    LEFT JOIN {{ ref('dim_products') }} p ON ca.product_id = p.product_id AND p.is_current = TRUE
    LEFT JOIN {{ ref('dim_brand') }} b ON p.brand_key = b.brand_key
    LEFT JOIN {{ ref('dim_sub_category') }} sc ON p.sub_category_key = sc.sub_category_key
    LEFT JOIN {{ ref('dim_main_category') }} mc ON sc.main_category_key = mc.main_category_key
)

SELECT * FROM final_mart
ORDER BY user_crm_id, activity_timestamp
