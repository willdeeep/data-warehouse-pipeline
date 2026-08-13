/*
===================================================================================
MODEL: dim_devices
===================================================================================

PURPOSE:
    Device dimension table for digital analytics and user experience analysis.
    Standardizes device, browser, and operating system classifications.

SOURCE:
    - {{ ref('stg_sessions') }}

GRAIN:
    One row per unique device/browser/OS combination

KEY ATTRIBUTES:
    - Device type categorization
    - Browser and OS standardization
    - Technology stack identification
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['device_key'], 'type': 'btree'},
        {'columns': ['device_type'], 'type': 'btree'}
    ]
) }}

WITH device_combinations AS (
    SELECT DISTINCT
        device_category AS device_type,
        'Unknown' AS browser,  -- Browser info not available in stg_sessions
        'Unknown' AS os,       -- OS info not available in stg_sessions
        MIN(dbt_valid_from) AS first_seen_at,
        MAX(dbt_updated_at) AS last_seen_at

    FROM {{ ref('stg_sessions') }}
    WHERE device_category IS NOT NULL
    GROUP BY 1, 2, 3
),

device_dimension AS (
    SELECT
        -- Primary key: simple integer ID
        ROW_NUMBER() OVER (ORDER BY device_type, browser, os) AS device_key,

        -- Standardize device type
        CASE
            WHEN LOWER(device_type) IN ('mobile', 'smartphone', 'phone') THEN 'Mobile'
            WHEN LOWER(device_type) IN ('tablet', 'ipad') THEN 'Tablet'
            WHEN LOWER(device_type) IN ('desktop', 'computer', 'pc', 'mac') THEN 'Desktop'
            WHEN LOWER(device_type) IN ('tv', 'smart tv', 'connected tv') THEN 'Connected TV'
            ELSE 'Other'
        END AS device_type,

        -- Standardize browser names
        CASE
            WHEN LOWER(browser) LIKE '%chrome%' THEN 'Chrome'
            WHEN LOWER(browser) LIKE '%safari%' THEN 'Safari'
            WHEN LOWER(browser) LIKE '%firefox%' THEN 'Firefox'
            WHEN LOWER(browser) LIKE '%edge%' THEN 'Edge'
            WHEN LOWER(browser) LIKE '%internet explorer%' OR LOWER(browser) LIKE '%ie%' THEN 'Internet Explorer'
            WHEN LOWER(browser) LIKE '%opera%' THEN 'Opera'
            ELSE COALESCE(browser, 'Unknown')
        END AS browser,

        -- Standardize OS names
        CASE
            WHEN LOWER(os) LIKE '%windows%' THEN 'Windows'
            WHEN LOWER(os) LIKE '%mac%' OR LOWER(os) LIKE '%osx%' THEN 'macOS'
            WHEN LOWER(os) LIKE '%ios%' THEN 'iOS'
            WHEN LOWER(os) LIKE '%android%' THEN 'Android'
            WHEN LOWER(os) LIKE '%linux%' THEN 'Linux'
            ELSE COALESCE(os, 'Unknown')
        END AS os,

        -- dbt metadata
        last_seen_at AS dbt_updated_at,
        first_seen_at AS dbt_created_at

    FROM device_combinations
)

SELECT * FROM device_dimension
