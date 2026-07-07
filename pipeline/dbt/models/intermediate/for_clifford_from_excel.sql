{{ config(
    materialized='table',
    indexes=[
        {'columns': ['date_key'], 'type': 'btree'},
        {'columns': ['source'], 'type': 'btree'}
    ]
) }}

WITH adplatorm_numbers AS (
  SELECT
    ad.date_key,
    a.platform_name,
    cost,
    clicks,
    impressions
  FROM
    loom-insights.warehouse.fact_advertising AS ad
  LEFT JOIN
    {{ ref('dim_ad_platform') }} AS a
  ON 
    a.platform_key = ad.platform_key
),
source_join AS (
  SELECT
    n.date_key,
    source_key,
    source,
    n.cost,
    n.impressions,
    n.clicks
  FROM 
    {{ ref('dim_source') }}  AS s
  LEFT JOIN 
    adplatorm_numbers AS n
  ON 
    s.source = n.platform_name
),
session_join AS (
  SELECT 
    s.date_key,
    s.source_key,
    source,
    cost,
    impressions,
    clicks
  FROM 
  source_join AS sj
  LEFT JOIN 
    {{ ref('fact_sessions') }} AS s
  ON 
    s.source_key = sj.source_key AND sj.date_key = s.date_key
  order by 
    sj.date_key
),
daily_transaction_total AS(
  SELECT 
    t.date_key,
    source,
    ROUND(SUM(transaction_total),2) AS daily_transaction_total,
    count(t.transaction_id) AS conversions,
  FROM 
    {{ ref('fact_transactions') }} AS t
  LEFT JOIN 
    {{ ref('fact_sessions') }} AS s
  ON
    t.session_id = s.session_id
  LEFT JOIN
    {{ ref('dim_source') }}AS so
  ON 
    so.source_key = s.source_key
  GROUP BY 
    date_key, source 
),
conversion_rate AS (
  SELECT 
    date_key,
    source,
    count(session_id) AS session_num
  FROM 
    {{ ref('fact_sessions') }} AS s
  LEFT JOIN 
    {{ ref('dim_source') }} AS so
  ON s.source_key =so.source_key
  GROUP BY date_key, source
)

SELECT 
  t.date_key, 
  t.source, 
  cost, 
  clicks, 
  impressions, 
  daily_transaction_total,
  round(t.conversions / session_num * 100,2) AS conversion_rate,
  CASE WHEN cost = 0 then null
  else ROUND(daily_transaction_total / cost * 100, 2) END AS ROAS
FROM
  session_join AS s
LEFT JOIN 
  daily_transaction_total AS t
ON 
  t.date_key = s.date_key AND t.source = s.source
LEFT JOIN
  conversion_rate AS c
ON
  c.source = s.source AND c.date_key = s.date_key
WHERE 
  t.date_key IS NOT NULL
group by 
  t.date_key, source, cost, clicks, impressions, daily_transaction_total, session_num, t.conversions
order by 
  t.date_key ASC, source ASC