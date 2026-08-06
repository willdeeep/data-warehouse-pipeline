-- Guards the UNION ALL in rpt_customer_activity: both 'profile_change' and 'transaction'
-- rows must be present. Fails (returns a row) if fewer than two distinct activity_types.
WITH distinct_types AS (
    SELECT COUNT(DISTINCT activity_type) AS n_types
    FROM {{ ref('rpt_customer_activity') }}
)
SELECT n_types
FROM distinct_types
WHERE n_types < 2
