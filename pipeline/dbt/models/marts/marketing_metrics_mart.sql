--date
--platform (e.g., Google, Meta, etc.)
--impressions, clicks, cost
--CTR = clicks / impressions
--CPC = cost / clicks
--Spend = cost


SELECT
    CAST(REPLACE(CAST(date AS STRING), '-', '') AS INT64) as date_key,
    ad_platform,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(cost) AS spend,
   
    -- Calculate CTR and CPC
    SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) AS ctr,
    SAFE_DIVIDE(SUM(cost), NULLIF(SUM(clicks), 0)) AS cpc
FROM {{ ref('stg_adplatform_data_unpivoted') }}
GROUP BY
    date,
    ad_platform
ORDER BY
    date DESC
