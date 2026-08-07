# Business Metrics & BI Use-Cases

## What this document is

This is the **analytics layer's use-case catalogue**: the business questions the `rpt_` marts are
built to answer, each with a query that runs against the actual warehouse models. It doubles as the
portfolio's "so what" — the BI narrative the warehouse exists to support.

> **Two things are deliberately separated here:**
>
> 1. **The queries are real.** They target the shipped marts/facts (`rpt_daily_channel_performance`,
>    `rpt_transactions`, `rpt_customer_activity`, `fct_sessions`) with their real column names, and
>    run as-is against the warehouse.
> 2. **The headline figures and projections are illustrative.** The dev/staging warehouse is built
>    from a **~500-user deterministic Faker seed** (see `data_generation/`), not production traffic.
>    Any "$X annual revenue / Y% conversion uplift" narrative below is a **hypothetical business
>    case** for how the model *would* be read at production scale — it is not measured from the seed.
>    Run the queries to get the real seeded numbers.

### Dataset naming

Marts materialize into the environment's warehouse dataset — `dev_warehouse` (dev),
`stg_warehouse` (staging), `warehouse` (prod). Examples below use `dev_warehouse`; swap the prefix
for the environment you're querying (see [RELEASE.md](../RELEASE.md) §Multi-environment naming).

---

## 1. Channel & acquisition performance

**Mart:** `rpt_daily_channel_performance` (grain: one row per `date` × `channel` × `platform`).

```sql
-- Daily-to-monthly channel performance: spend, sessions, conversions, revenue, ROAS
SELECT
  DATE_TRUNC(date, MONTH)                        AS month,
  channel,
  SUM(ad_spend)                                  AS ad_spend,
  SUM(sessions)                                  AS sessions,
  SUM(new_users)                                 AS new_users,
  SUM(transaction_count)                         AS transactions,
  SUM(total_revenue)                             AS revenue,
  SAFE_DIVIDE(SUM(transaction_count), SUM(sessions)) AS conversion_rate,
  SAFE_DIVIDE(SUM(total_revenue), SUM(ad_spend))     AS roas
FROM `dev_warehouse.rpt_daily_channel_performance`
GROUP BY month, channel
ORDER BY month, revenue DESC
```

This mart already joins advertising spend (`fct_advertising`), session engagement (`fct_sessions`),
and transaction revenue (`fct_transactions`) by date/channel/platform, so ROAS and conversion rate
are a single grouped scan — no cross-fact joins at query time.

## 2. Transaction revenue & profitability

**Mart:** `rpt_transactions` (grain: one row per **unit sold**, `item_id`).

```sql
-- Monthly revenue, profit, and return rate by product category
SELECT
  DATE_TRUNC(transaction_date, MONTH)   AS month,
  product_main_category,
  COUNT(DISTINCT item_id)               AS units_sold,
  SUM(quantity)                         AS quantity,
  SUM(revenue)                          AS revenue,
  SUM(gross_profit)                     AS gross_profit,
  SUM(net_revenue)                      AS net_revenue,          -- revenue - refunds
  SAFE_DIVIDE(SUM(gross_profit), SUM(revenue))                 AS gross_margin,
  COUNTIF(return_status IS NOT NULL)    AS returned_units,
  SAFE_DIVIDE(COUNTIF(return_status IS NOT NULL), COUNT(*))    AS return_rate
FROM `dev_warehouse.rpt_transactions`
GROUP BY month, product_main_category
ORDER BY month, revenue DESC
```

Because the grain is per-unit with a globally-unique `item_id` (#56), a partial return of one of two
identical items is counted correctly — `net_revenue` and `return_rate` reflect the individual unit,
not the whole line.

```sql
-- Average order value (roll units back up to the transaction)
WITH per_txn AS (
  SELECT transaction_id, user_crm_id, SUM(revenue) AS order_revenue
  FROM `dev_warehouse.rpt_transactions`
  GROUP BY transaction_id, user_crm_id
)
SELECT
  COUNT(*)                              AS orders,
  COUNT(DISTINCT user_crm_id)           AS purchasing_customers,
  ROUND(AVG(order_revenue), 2)          AS avg_order_value,
  ROUND(SUM(order_revenue), 2)          AS total_revenue
FROM per_txn
```

## 3. Customer lifecycle & LTV

**Mart:** `rpt_customer_activity` (grain: one row per customer activity event; SCD-chronology).

```sql
-- Customer journey: activity mix and segmentation over time
SELECT
  DATE_TRUNC(activity_date, MONTH)      AS month,
  activity_type,                        -- profile_change | transaction | session
  customer_state_at_time,               -- New | Repeat | Loyal | Premium Customer
  COUNT(*)                              AS events,
  COUNT(DISTINCT user_crm_id)           AS customers
FROM `dev_warehouse.rpt_customer_activity`
GROUP BY month, activity_type, customer_state_at_time
ORDER BY month, events DESC
```

```sql
-- Latest lifetime value per customer (current SCD2 version)
SELECT
  user_crm_id,
  loom_plus_status,
  loom_plus_tier,
  lifetime_orders,
  lifetime_value
FROM `dev_warehouse.dim_users`
WHERE is_current
ORDER BY lifetime_value DESC
LIMIT 100
```

Because `dim_users` is SCD Type 2, transactions join point-in-time to the customer state *as of the
purchase*, so `customer_state_at_time` reflects the segment the customer was in at that moment — not
their state today.

## 4. Session engagement & conversion funnel

**Fact:** `fct_sessions` (grain: one row per `session_id`).

```sql
-- Session engagement and session-level conversion
SELECT
  DATE_TRUNC(dd.date, MONTH)                     AS month,
  COUNT(*)                                       AS sessions,
  COUNTIF(fs.bounce_flag)                        AS bounces,
  SAFE_DIVIDE(COUNTIF(fs.bounce_flag), COUNT(*)) AS bounce_rate,
  ROUND(AVG(fs.session_duration_seconds), 1)     AS avg_duration_seconds,
  SUM(fs.page_views)                             AS page_views,
  COUNTIF(fs.transaction_count > 0)              AS converting_sessions,
  SAFE_DIVIDE(COUNTIF(fs.transaction_count > 0), COUNT(*)) AS session_conversion_rate
FROM `dev_warehouse.fct_sessions` fs
JOIN `dev_warehouse.dim_date` dd USING (date_key)
GROUP BY month
ORDER BY month
```

`session_duration_seconds` is NULL for bounced (single-page) sessions, so `AVG` correctly reflects
engaged sessions only; the funnel is derived from the `bounce_flag` / `add_to_cart_flag` /
`transaction_count` flags computed in `fct_sessions` from the underlying funnel events.

---

## Illustrative business case (hypothetical, production-scale)

> The numbers in this section are **not** measured from the Faker seed. They illustrate how the
> warehouse would frame a growth business case if pointed at production-scale traffic. Treat them as
> a narrative example of the decisions the marts above are meant to inform.

### Conversion-rate opportunity
- **Session conversion** (from query §4) is the lever: a move from ~2.0% → 3.0% at production volume
  is a material revenue swing, and the daily channel mart (§1) localises *which* channels drag the
  blended rate down.
- **Checkout completion** and **AOV** (§2) compound with it — the profitability query already exposes
  category-level margin and return rate, so uplift can be modelled net of refunds, not just on
  top-line revenue.

### What to track (all answerable from the marts above)
1. Blended and per-channel conversion rate — §1, §4
2. ROAS by channel/platform — §1
3. Gross margin and return rate by category — §2
4. AOV and repeat-purchase mix — §2, §3
5. LTV by segment / Loom+ tier — §3

The point of the layered warehouse is that each of these is a single grouped scan over a mart, not a
bespoke multi-table join — which is what makes the "then vs now" performance story in
[erd.md](erd.md) real rather than rhetorical.
