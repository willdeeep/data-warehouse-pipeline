/*
===================================================================================
SCD TYPE 2 VALIDATION TESTS
===================================================================================

Comprehensive tests to validate SCD Type 2 implementation across dimensions
and marts. These tests ensure proper temporal logic and data integrity.
*/

-- ===================================================================================
-- TEST 1: CUSTOMER ACTIVITY MART SCD VALIDATION
-- ===================================================================================

-- Validate that point-in-time joins in rpt_customer_activity work correctly
WITH transaction_scd_validation AS (
    SELECT 
        cam.user_crm_id,
        cam.activity_date,
        cam.customer_version_key,
        cam.loom_plus_status,
        cam.loom_plus_tier,
        cam.lifetime_value,
        -- Check if transaction date falls within SCD valid period
        u.valid_from,
        u.valid_to,
        u.is_current,
        CASE 
            WHEN cam.activity_date >= CAST(u.valid_from AS DATE) 
                AND (u.valid_to IS NULL OR cam.activity_date < CAST(u.valid_to AS DATE))
            THEN 'VALID_SCD_JOIN'
            ELSE 'INVALID_SCD_JOIN'
        END AS scd_join_validity
    FROM {{ ref('rpt_customer_activity') }} cam
    LEFT JOIN {{ ref('dim_users') }} u ON cam.customer_version_key = u.user_surrogate_key
   WHERE cam.activity_type = 'transaction' 
       AND cam.user_crm_id IS NOT NULL
    LIMIT 1000
),

-- Validate profile changes represent actual SCD transitions
profile_change_validation AS (
    SELECT 
        cam.user_crm_id,
        cam.activity_date,
        cam.change_type,
        cam.customer_version_key,
        -- Check if this matches an actual SCD record transition
        COUNT(*) OVER (PARTITION BY cam.user_crm_id ORDER BY cam.activity_date) as sequence_check
    FROM {{ ref('rpt_customer_activity') }} cam
    WHERE cam.activity_type = 'profile_change' 
        AND cam.user_crm_id IS NOT NULL
    LIMIT 500
)

-- Only return INVALID SCD joins (failures)
SELECT 
    CAST(cam.user_crm_id AS STRING) as user_crm_id,
    CAST(cam.activity_date AS STRING) as activity_date,
    CAST(cam.customer_version_key AS STRING) as customer_version_key,
    'INVALID_SCD_JOIN' as failure_reason
FROM {{ ref('rpt_customer_activity') }} cam
LEFT JOIN {{ ref('dim_users') }} u ON cam.customer_version_key = u.user_surrogate_key
WHERE cam.activity_type = 'transaction' 
    AND cam.user_crm_id IS NOT NULL
    AND NOT (
        cam.activity_date >= CAST(u.valid_from AS DATE) 
        AND (u.valid_to IS NULL OR cam.activity_date < CAST(u.valid_to AS DATE))
    )

UNION ALL

-- Only return invalid customer journey sequences (failures)
SELECT 
    CAST(cam.user_crm_id AS STRING) as user_crm_id,
    'N/A' as activity_date,
    'N/A' as customer_version_key,
    'INVALID_CUSTOMER_SEQUENCE' as failure_reason
FROM {{ ref('rpt_customer_activity') }} cam
GROUP BY cam.user_crm_id
HAVING COUNT(*) > 1 
    AND MAX(cam.customer_activity_sequence) != COUNT(*)
LIMIT 100
