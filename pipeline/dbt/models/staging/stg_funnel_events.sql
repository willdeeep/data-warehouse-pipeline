
/*
===================================================================================
MODEL: stg_funnel_events
===================================================================================

PURPOSE:
    Staging model for user funnel event tracking data used in conversion 
    analysis and customer journey mapping.

SOURCE:
    - loom_sync.funnelevents (raw user behavior tracking events)

BUSINESS LOGIC:
    - Preserves all event tracking fields for funnel analysis
    - Maintains event sequence and timing information
    - Links events to users, sessions, and transactions
    - Supports conversion funnel and drop-off analysis

GRAIN:
    One row per user event occurrence

KEY TRANSFORMATIONS:
    1. Date validation (excludes null event dates)
    2. Preservation of event context and identifiers
    3. Addition of dbt metadata timestamps

DATA QUALITY:
    - Ensures all events have valid dates
    - Maintains event sequence integrity
    - Preserves user and session context

ROW DEFINITION:
    Each row represents a single user interaction event with timing,
    context, and associated product or transaction information.
===================================================================================
*/


WITH cleaned_funnel_events AS (
    SELECT
        -- Original source columns with SAFE_CAST where needed for data types
        SAFE_CAST(date AS DATE) as date,
        event_time,
        user_cookie_id,
        SAFE_CAST(user_crm_id AS INTEGER) AS user_crm_id,
        session_id,
        device_category,
        event_name,
        SAFE_CAST(item_id AS INTEGER) AS item_id,
        SAFE_CAST(transaction_id AS INTEGER) AS transaction_id,
        
        -- Add metadata
        CURRENT_TIMESTAMP as dbt_updated_at,
        CURRENT_DATE as dbt_valid_from
        
    FROM {{ source('loom_sync', 'funnelevents') }}
    WHERE date IS NOT NULL
)

SELECT * FROM cleaned_funnel_events


