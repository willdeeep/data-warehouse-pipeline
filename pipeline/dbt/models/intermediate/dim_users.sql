/*
===================================================================================
MODEL: dim_users
===================================================================================

PURPOSE:
    User dimension table with customer attributes and lifetime metrics.
    Implements Slowly Changing Dimension Type 2 logic for tracking user profile changes over time.

SOURCE:
    - {{ ref('stg_users') }}

GRAIN:
    One row per unique user per time period (user_crm_id + valid_from)

KEY ATTRIBUTES:
    - User demographics and profile information
    - Customer lifecycle dates
    - Lifetime value and transaction metrics
    - Subscription status information
    - SCD Type 2 tracking fields

SCD LOGIC:
    - Tracks changes in user attributes over time
    - Tracked attributes include:
        - city,
        - gender
        - opt_in_status,
        - loom_plus_status,
        - loom_plus_tier
    - Creates new records when changes are detected
    - Maintains historical versions with valid_from/valid_to dates
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['user_surrogate_key'], 'type': 'btree'},
        {'columns': ['user_crm_id'], 'type': 'btree'},
        {'columns': ['is_current'], 'type': 'btree'},
        {'columns': ['valid_from', 'valid_to'], 'type': 'btree'}
    ]
) }}

WITH users_source AS (
    SELECT
        -- Natural key
        user_crm_id,
        
        -- Source attributes (trackable for changes)
        city,
        user_gender AS gender,
        opt_in_status,
        loom_plus_status,
        CASE 
            WHEN loom_plus_status = TRUE THEN loom_plus_tier
            ELSE NULL 
        END AS loom_plus_tier,
        
        -- Date attributes (less frequently changing)
        registration_date,
        latest_login_date,
        first_purchase_date,
        latest_purchase_date AS last_purchase_date,
        
        -- Calculated metrics (will change over time)
        transaction_count AS lifetime_orders,
        total_revenue AS lifetime_value,
        
        -- Metadata for SCD tracking
        dbt_updated_at,
        dbt_valid_from
        
    FROM {{ ref('stg_users') }}
    WHERE user_crm_id IS NOT NULL
),

-- Create change history by detecting when tracked attributes change
user_changes AS (
    SELECT 
        user_crm_id,
        city,
        gender,
        opt_in_status,
        loom_plus_status,
        loom_plus_tier,
        registration_date,
        latest_login_date,
        first_purchase_date,
        last_purchase_date,
        lifetime_orders,
        lifetime_value,
        dbt_updated_at,
        dbt_valid_from,
        
        -- Create a signature for change detection
        {{ dbt_utils.generate_surrogate_key([
            'city',
            'gender', 
            'opt_in_status',
            'loom_plus_status',
            'loom_plus_tier'
        ]) }} AS change_signature,
        
        -- Determine valid_from based on available dates
        COALESCE(
            TIMESTAMP(registration_date),
            TIMESTAMP(first_purchase_date),
            CURRENT_TIMESTAMP()
        ) AS calculated_valid_from
        
    FROM users_source
),

-- For this simplified approach, we'll create one record per user with current data
-- In a production environment, you would typically implement this as a snapshot
-- or use a more sophisticated change detection mechanism

tier_function AS (
SELECT
  s.user_crm_id,
  CASE
    WHEN count(DISTINCT transaction_id) IS NULL THEN 'unqualified'
    WHEN count(DISTINCT transaction_id) = 1 THEN 'bronze'
    WHEN count(DISTINCT transaction_id) = 2 THEN 'silver'
    WHEN count(DISTINCT transaction_id) = 3 THEN 'gold'
    WHEN count(DISTINCT transaction_id) < 4 THEN 'platinum'
    ELSE 'unqualified' END AS loom_plus_tier
FROM 
  {{ ref('stg_sessions') }} s
LEFT JOIN 
  {{ ref('stg_transactions') }} t
USING(session_id) 
WHERE 
  s.user_crm_id IS NOT NULL
GROUP BY 
  s.user_crm_id
),

final AS (
    SELECT 
        {{ dbt_utils.generate_surrogate_key(['uc.user_crm_id', 'uc.calculated_valid_from']) }} AS user_surrogate_key,
        uc.user_crm_id,
        city,
        gender,
        opt_in_status,
        loom_plus_status,
        loom_plus_tier,
        registration_date,
        latest_login_date,
        first_purchase_date,
        last_purchase_date,
        lifetime_orders,
        lifetime_value,
        
        -- SCD Type 2 fields
        calculated_valid_from AS valid_from,
        CAST(NULL AS TIMESTAMP) AS valid_to,
        TRUE AS is_current,
        
        -- Metadata
        dbt_updated_at,
        CURRENT_TIMESTAMP() AS dbt_created_at
        
    FROM user_changes AS uc
)

SELECT * FROM final
