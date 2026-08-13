/*
===================================================================================
MART: rpt_transactions
===================================================================================

PURPOSE:
    Comprehensive transaction-level mart combining transactional data with
    dimensional context, profit calculations, and refund information.

GRAIN:
    One row per transaction line item (transaction_id + product_id combination)

SOURCES:
    - fct_transactions (core layer)
    - dim_date (core layer)
    - dim_users (core layer)
    - dim_products (core layer)
    - fct_sessions (core layer)

Key Dimensions:
    - Date of transaction and year/month/day values linked in from dim_date
    - Product/item name, category, sub_category, and brand from dim_products
    - User CRM ID from dim_users (null if guest checkout)
    - User Cookie ID for anonymous user tracking and session analysis
    - Loom+ status from dim_users (null if not a registered user and/or not loom plus)
    - Session ID from fct_sessions for attribution analysis
    - Marketing campaign and traffic source from fct_sessions

KEY METRICS:
    - Revenue and cost calculations
    - Gross profit and net profit (after refunds)
    - Refund amounts and status
    - Dimensional context for analysis

BUSINESS VALUE:
    - Complete view of transaction profitability
    - Refund impact analysis
    - Customer and product performance metrics
    - Session attribution for transactions
===================================================================================
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['date_key'], 'type': 'btree'},
        {'columns': ['user_crm_id'], 'type': 'btree'},
        {'columns': ['user_cookie_id'], 'type': 'btree'},
        {'columns': ['product_id'], 'type': 'btree'}
    ]
) }}

SELECT
  ft.item_id AS item_id,
  ft.date_key,
  ft.user_crm_id AS user_crm_id,
  ft.user_cookie_id AS user_cookie_id,
  ft.session_id,
  ft.product_id AS product_id,

  -- Date dimension attributes
  d.date AS transaction_date,
  d.year AS transaction_year,
  d.month AS transaction_month,
  d.day_of_week AS transaction_day_of_week,
  d.quarter AS transaction_quarter,
  d.is_weekend,
  d.is_holiday,

  -- Product dimension attributes (from current SCD version)
  p.name AS product_name,
  b.brand_name AS product_brand,
  mc.main_category_name AS product_main_category,
  sc.sub_category_name AS product_sub_category,
  p.gender_target AS product_gender_target,
  p.list_price AS product_list_price,

  -- User dimension attributes (from current SCD version, null for guest checkout)
  u.city AS user_city,
  u.gender AS user_gender,
  u.registration_date AS user_registration_date,
  u.lifetime_orders AS user_lifetime_orders,
  u.lifetime_value AS user_lifetime_value,
  u.loom_plus_status AS user_loom_plus_status,

  -- Transaction metrics
  ft.transaction_coupon IS NOT NULL AS coupon_flag,
  ft.return_status,
  ft.product_quantity AS quantity,
  ft.product_revenue AS revenue,
  p.unit_cost * ft.product_quantity AS cost,
  -- Calculate gross profit using product dimension unit cost
  ft.product_revenue - (p.unit_cost * ft.product_quantity) AS gross_profit,
  -- Refund amount calculation
  CASE
    WHEN ft.return_status = 'Refund' THEN ft.product_price * COALESCE(ft.return_quantity, 0)
    ELSE 0
  END AS refund_amount,
  -- Net revenue after refunds
  ft.product_revenue -
    CASE
      WHEN ft.return_status = 'Refund' THEN ft.product_price * COALESCE(ft.return_quantity, 0)
      ELSE 0
    END AS net_revenue
FROM {{ ref('fct_transactions') }} ft
LEFT JOIN {{ ref('dim_date') }} d ON ft.date_key = d.date_key
-- Join to current version of user dimension using SCD Type 2 logic
LEFT JOIN {{ ref('dim_users') }} u ON ft.user_crm_id = u.user_crm_id AND u.is_current = TRUE
-- Join to current version of product dimension using SCD Type 2 logic
LEFT JOIN {{ ref('dim_products') }} p ON ft.product_id = p.product_id AND p.is_current = TRUE
LEFT JOIN {{ ref('dim_brand') }} b ON p.brand_key = b.brand_key
LEFT JOIN {{ ref('dim_sub_category') }} sc ON p.sub_category_key = sc.sub_category_key
LEFT JOIN {{ ref('dim_main_category') }} mc ON sc.main_category_key = mc.main_category_key
