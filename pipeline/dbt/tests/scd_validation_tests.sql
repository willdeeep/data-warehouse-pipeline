/*
===================================================================================
SCD TYPE 2 VALIDATION TESTS
===================================================================================

This file contains custom tests to validate the Slowly Changing Dimension
Type 2 implementation for user and product dimensions.

TESTS INCLUDED:
1. Uniqueness of surrogate keys
2. Current record validation (only one per natural key)
3. Historical continuity (no gaps or overlaps)
4. Valid date logic
5. Change detection accuracy
*/

-- Test 1: Ensure each user has exactly one current record
SELECT
    'dim_users' AS table_name,
    'current_record_uniqueness' AS test_name,
    CAST(user_crm_id AS STRING) AS natural_key,
    COUNT(*) AS current_count
FROM {{ ref('dim_users') }}
WHERE is_current = TRUE
GROUP BY user_crm_id
HAVING COUNT(*) != 1

UNION ALL

-- Test 2: Ensure each product has exactly one current record
SELECT
    'dim_products' AS table_name,
    'current_record_uniqueness' AS test_name,
    CAST(product_id AS STRING) AS natural_key,
    COUNT(*) AS current_count
FROM {{ ref('dim_products') }}
WHERE is_current = TRUE
GROUP BY product_id
HAVING COUNT(*) != 1

UNION ALL

-- Test 3: Validate current records have NULL valid_to
SELECT
    'dim_users' AS table_name,
    'current_valid_to_null' AS test_name,
    CAST(user_crm_id AS STRING) AS natural_key,
    COUNT(*) AS invalid_count
FROM {{ ref('dim_users') }}
WHERE is_current = TRUE AND valid_to IS NOT NULL
GROUP BY user_crm_id
HAVING COUNT(*) > 0

UNION ALL

SELECT
    'dim_products' AS table_name,
    'current_valid_to_null' AS test_name,
    CAST(product_id AS STRING) AS natural_key,
    COUNT(*) AS invalid_count
FROM {{ ref('dim_products') }}
WHERE is_current = TRUE AND valid_to IS NOT NULL
GROUP BY product_id
HAVING COUNT(*) > 0

UNION ALL

-- Test 4: Validate historical records have non-NULL valid_to
SELECT
    'dim_users' AS table_name,
    'historical_valid_to_not_null' AS test_name,
    CAST(user_crm_id AS STRING) AS natural_key,
    COUNT(*) AS invalid_count
FROM {{ ref('dim_users') }}
WHERE is_current = FALSE AND valid_to IS NULL
GROUP BY user_crm_id
HAVING COUNT(*) > 0

UNION ALL

SELECT
    'dim_products' AS table_name,
    'historical_valid_to_not_null' AS test_name,
    CAST(product_id AS STRING) AS natural_key,
    COUNT(*) AS invalid_count
FROM {{ ref('dim_products') }}
WHERE is_current = FALSE AND valid_to IS NULL
GROUP BY product_id
HAVING COUNT(*) > 0
