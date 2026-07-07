/*
===================================================================================
DIM_PRODUCTS SCD TYPE 2 VALIDATION TESTS
===================================================================================

Validates the SCD Type 2 implementation for the products dimension table.
Tests proper versioning, temporal logic, and data integrity.

This test returns only FAILING records (0 rows = all tests pass).
*/

WITH products_scd_structure AS (
    SELECT 
        product_id,
        COUNT(*) as version_count,
        COUNT(CASE WHEN is_current = TRUE THEN 1 END) as current_count,
        COUNT(CASE WHEN is_current = FALSE THEN 1 END) as historical_count
    FROM {{ ref('dim_products') }}
    GROUP BY product_id
),

temporal_integrity AS (
    SELECT 
        product_id,
        product_surrogate_key,
        valid_from,
        valid_to,
        is_current,
        LAG(valid_to) OVER (PARTITION BY product_id ORDER BY valid_from) as prev_valid_to,
        CASE 
            WHEN LAG(valid_to) OVER (PARTITION BY product_id ORDER BY valid_from) IS NOT NULL
                AND LAG(valid_to) OVER (PARTITION BY product_id ORDER BY valid_from) != valid_from
            THEN 'TEMPORAL_GAP_OR_OVERLAP'
            WHEN is_current = TRUE AND valid_to IS NOT NULL
            THEN 'CURRENT_RECORD_HAS_END_DATE'
            WHEN is_current = FALSE AND valid_to IS NULL
            THEN 'HISTORICAL_RECORD_MISSING_END_DATE'
            ELSE 'VALID_TEMPORAL_STRUCTURE'
        END as temporal_validation
    FROM {{ ref('dim_products') }}
)

-- Return only products with NO current record (SCD problem)
SELECT 
    CAST(product_id AS STRING) as product_id,
    'NO_CURRENT_RECORD' as issue_type,
    CAST(current_count AS STRING) as issue_count,
    'Product has no current version' as issue_description
FROM products_scd_structure
WHERE current_count = 0

UNION ALL

-- Return only products with MULTIPLE current records (SCD problem)
SELECT 
    CAST(product_id AS STRING) as product_id,
    'MULTIPLE_CURRENT_RECORDS' as issue_type,
    CAST(current_count AS STRING) as issue_count,
    'Product has multiple current versions' as issue_description
FROM products_scd_structure
WHERE current_count > 1

UNION ALL

-- Return only records with temporal integrity problems
SELECT 
    CAST(product_id AS STRING) as product_id,
    temporal_validation as issue_type,
    '1' as issue_count,
    'Temporal integrity violation' as issue_description
FROM temporal_integrity
WHERE temporal_validation != 'VALID_TEMPORAL_STRUCTURE'
LIMIT 100
