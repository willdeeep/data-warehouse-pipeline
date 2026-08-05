-- Guards the UNION ALL in rpt_customer_activity: both 'profile_change' and 'transaction'
-- rows should be present. Returns a row if fewer than two distinct activity_types.
--
-- severity=warn (not error) for now: dim_users has no SCD2 history yet (the source `users`
-- table is a single snapshot — one row per user_crm_id), so the profile_change branch is
-- currently empty and only 'transaction' rows exist. This test warns until the SCD2 build-out
-- (datagen emits versioned user history → real SCD2 in dim_users) lands, after which it should
-- be flipped back to severity=error. See the dim-users-scd2 feature work.
{{ config(severity='warn') }}
WITH distinct_types AS (
    SELECT COUNT(DISTINCT activity_type) AS n_types
    FROM {{ ref('rpt_customer_activity') }}
)
SELECT n_types
FROM distinct_types
WHERE n_types < 2
