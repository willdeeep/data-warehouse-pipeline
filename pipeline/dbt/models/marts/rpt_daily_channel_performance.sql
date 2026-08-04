{{ config(materialized='table') }}

WITH base AS (
    SELECT
        -- Date dimensions
        d.date AS date,
        EXTRACT(WEEK FROM CAST(d.date AS DATE)) AS week_number,
        d.day_of_week,
        d.month,
        d.year,

        -- Acquisition & Ad metrics
        dap.channel_type AS channel,         -- e.g., Paid Social, Search, etc.
        dap.platform_name AS platform,
        fa.clicks,                           -- Note: Will repeat for each device if ad data is not device-specific
        dd.device_type AS device,
        fa.impressions,                      -- Note: Will repeat for each device if ad data is not device-specific
        fa.cost AS ad_spend,                 -- Note: Will repeat for each device if ad data is not device-specific

        -- Engagement
        COUNT(DISTINCT fs.session_id) AS sessions,
        COUNT(DISTINCT fs.user_crm_id) AS total_users,
        COUNT(DISTINCT CASE WHEN du.registration_date = d.date THEN fs.user_crm_id END) AS new_users,
        SUM(CASE WHEN fs.bounce_flag THEN 1 ELSE 0 END) AS bounces,
        SUM(COALESCE(fs.page_views, 0)) AS page_views,
        AVG(fs.session_duration_seconds) AS avg_session_duration,

        -- Conversion & Revenue
        COUNT(DISTINCT ft.transaction_id) AS transaction_count,
        SUM(COALESCE(ft.transaction_revenue, 0)) AS total_revenue,
        SUM(COALESCE(ft.product_quantity, 0)) AS item_quantity,
        SUM(COALESCE(ft.product_price * ft.product_quantity, 0)) AS item_price_total

    FROM {{ ref('fct_advertising') }} fa
    LEFT JOIN {{ ref('dim_date') }} d
        ON fa.date_key = d.date_key
    LEFT JOIN {{ ref('dim_ad_platform') }} dap
        ON fa.platform_key = dap.platform_key
    -- Join to sessions on date and platform (device comes from sessions)
    LEFT JOIN {{ ref('fct_sessions') }} fs
        ON fa.date_key = fs.date_key
        AND fa.platform_key = fs.platform_key
    LEFT JOIN {{ ref('dim_devices') }} dd
        ON fs.device_key = dd.device_key
    LEFT JOIN {{ ref('dim_users') }} du
        ON fs.user_crm_id = du.user_crm_id AND du.is_current = TRUE
    LEFT JOIN {{ ref('fct_transactions') }} ft
        ON fs.session_id = ft.session_id
        AND fa.date_key = ft.date_key

    WHERE d.date BETWEEN DATE('2024-05-01') AND DATE('2024-06-30')
    GROUP BY
        d.date, week_number, d.day_of_week, d.month, d.year,
        dap.channel_type, dap.platform_name, dd.device_type, fa.clicks, fa.impressions, fa.cost
)

SELECT * FROM base
ORDER BY date, channel, platform, device
