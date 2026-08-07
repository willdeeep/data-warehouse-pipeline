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
        dbt_valid_from,

        -- SCD2 version effective date (from source history)
        valid_from AS source_valid_from

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

        -- Real SCD2 effective date (from source version history)
        TIMESTAMP(source_valid_from) AS calculated_valid_from

    FROM users_source
),

-- Determine each version's expiry by looking at the next version's valid_from
versioned AS (
    SELECT
        uc.*,
        LEAD(uc.calculated_valid_from) OVER (
            PARTITION BY uc.user_crm_id ORDER BY uc.calculated_valid_from
        ) AS next_valid_from
    FROM user_changes AS uc
),

final AS (
    SELECT
        {{ generate_int_surrogate_key(['user_crm_id', 'calculated_valid_from']) }} AS user_surrogate_key,
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

        -- SCD Type 2 fields (half-open [valid_from, valid_to))
        calculated_valid_from AS valid_from,
        next_valid_from AS valid_to,
        (next_valid_from IS NULL) AS is_current,

        -- Metadata
        dbt_updated_at,
        CURRENT_TIMESTAMP() AS dbt_created_at

    FROM versioned
)

SELECT * FROM final
