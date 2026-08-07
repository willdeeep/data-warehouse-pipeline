# Database Structure Evolution: Then vs Now

## Overview

This document illustrates the transformation of the Loom warehouse from a flat, unstructured
source layout into a layered dimensional data warehouse (staging → core → marts) with conformed
keys, a snowflaked ~3NF core, and SCD Type 2 history.

> **Source of truth.** The DBML below is kept in sync with the dbt model YAMLs
> (`pipeline/dbt/models/**/*.yml`). If they ever disagree, the YAML wins — treat this doc as the
> narrative overview and [dbt-build-summary.md](dbt-build-summary.md) as the validated build state.

## 🗃️ BEFORE: Legacy source structure (illustrative)

The upstream `loom_sync` mirror is a flat collection of tables with no enforced relationships,
no dimensional modelling, and no historical tracking — the raw shape the warehouse cleans up.
This section is an **illustrative** sketch of that "before" state, not a live schema.

```dbml
// Legacy source structure — flat tables, no proper joins (illustrative)
Project loom_legacy {
  database_type: 'BigQuery'
  Note: 'Raw loom_sync mirror — flat structure, no keys or history'
}

Table users {
  user_crm_id string [note: 'No enforced primary key']
  city string
  registration_date date
  loom_plus_status string
  Note: 'Raw user data — no data quality constraints'
}

Table transactions {
  transaction_id string [note: 'No enforced primary key']
  user_crm_id string [note: 'No foreign key relationship']
  date date
  transaction_revenue float
  Note: 'Transaction headers — no item detail relationship'
}

Table transactionitems {
  transaction_id string [note: 'No foreign key relationship']
  item_id string [note: 'No product catalog relationship']
  item_quantity int
  item_price float
  Note: 'Line items — orphaned from products'
}

Table sessions {
  session_id string [note: 'No enforced primary key']
  user_crm_id string [note: 'No foreign key relationship']
  date date
  device_category string
  traffic_source string
  traffic_medium string
  Note: 'Session data — no behavioural event linkage'
}

Table productattributes {
  item_id string [note: 'No enforced primary key']
  item_name string
  item_brand string
  item_main_category string
  item_sub_category string
  Note: 'Flat catalog — no hierarchy, no cost/price join'
}

Table funnelevents {
  session_id string [note: 'No foreign key relationship']
  event_time datetime
  event_name string
  Note: 'Raw events — no taxonomy or standardization'
}

Table adplatform_data {
  date date
  platform string
  impressions int
  clicks int
  cost int
  Note: 'Ad data in a wide per-platform layout — no attribution linkage'
}

// Legacy issues:
// 1. No primary/foreign key relationships
// 2. No data quality constraints
// 3. No dimensional modelling / conformed keys
// 4. No historical tracking (SCD)
// 5. No aggregated marts for analytics
```

## 🏗️ AFTER: Modern layered warehouse

The warehouse implements dimensional modelling with **conformed keys**, a **snowflaked ~3NF core**
(geo and product hierarchies broken out), and **SCD Type 2** history on the customer and product
dimensions. Naming: `stg_` (staging views) → `dim_`/`fct_`/`int_` (core) → `rpt_` (marts).

### Key conventions (see [dbt-build-summary.md](dbt-build-summary.md) §Data reconciliation, #36)

- **Natural keys are integer**: `user_crm_id`, `transaction_id`, `product_id`, `item_id`,
  `date_key` (`YYYYMMDD`). `session_id` and `user_cookie_id` stay **string** (the natural fit for
  session/cookie identifiers).
- **Warehouse surrogate/FK keys are deterministic signed INT64** hashes via the
  `generate_int_surrogate_key` macro (`FARM_FINGERPRINT(ARRAY_TO_STRING([...], '|'))`) —
  **conformed**, so a child computes the same key its parent stores (no lookup join). These are the
  `*_surrogate_key`, `country/region/brand/main_category/sub_category_key`, `platform_key`, `ad_key`.
- The `ROW_NUMBER`-assigned dimension keys (`geo_key`, `device_key`, `medium_key`, `source_key`)
  are plain integers.
- Types in the DBML below: `bigint` = INT64 conformed hash; `integer` = natural or row-number key.

```dbml
// Modern data warehouse — layered architecture with conformed keys and SCD2
Project loom_modern {
  database_type: 'BigQuery'
  Note: 'staging (views) -> core (snowflaked star, SCD2) -> marts (rpt_)'
}

//============================================================================
// STAGING LAYER — cleaned, standardized source (views)
//============================================================================
// stg_users, stg_transactions, stg_transactions_and_items, stg_sessions,
// stg_product_attributes, stg_product_costs, stg_product_list_prices,
// stg_product_returns, stg_funnel_events, stg_adplatform_data,
// stg_adplatform_data_unpivoted  (11 views total)

Table stg_users {
  user_crm_id integer [pk, note: 'Cast from source string; SAFE_CAST filtered to valid INT64']
  city string
  gender string
  registration_date date [not null]
  latest_login_date date
  first_purchase_date date
  latest_purchase_date date
  opt_in_status boolean
  loom_plus_status boolean
  loom_plus_tier string
  Note: 'Staging: cleaned user profiles (SCD2 history added downstream in dim_users)'
}

Table stg_transactions_and_items {
  transaction_id integer [not null]
  item_id integer [pk, note: 'Globally-unique per unit sold (#56)']
  date date [not null]
  item_price float [not null]
  item_quantity integer [not null]
  Note: 'Staging: transaction line items, one row per unit sold'
}

//============================================================================
// CORE LAYER — conformed dimensions + facts (snowflaked ~3NF)
//============================================================================

// ---- Customer (SCD Type 2) ----
Table dim_users {
  user_surrogate_key bigint [pk, note: 'Conformed INT64 hash of (user_crm_id, valid_from)']
  user_crm_id integer [not null, note: 'Natural key — many rows per user across versions']
  city string
  gender string
  registration_date date
  latest_login_date date
  first_purchase_date date
  last_purchase_date date
  opt_in_status boolean
  loom_plus_status boolean
  loom_plus_tier string
  lifetime_orders integer
  lifetime_value float
  valid_from timestamp [not null]
  valid_to timestamp [note: 'NULL for the current version']
  is_current boolean [not null]
  Note: 'Dimension: customer master, SCD Type 2 (one is_current per user)'
}

// ---- Product (SCD Type 2, keys-only; hierarchy snowflaked out) ----
Table dim_products {
  product_surrogate_key bigint [pk, note: 'Conformed INT64 hash of (product_id, valid_from)']
  product_id integer [not null, note: 'Natural key (SKU)']
  brand_key bigint [ref: > dim_brand.brand_key, note: 'FK — snowflaked out']
  sub_category_key bigint [ref: > dim_sub_category.sub_category_key, note: 'FK — main reachable via sub']
  name string
  gender_target string
  list_price float
  unit_cost float
  profit_margin float [note: '(list_price - unit_cost) / list_price']
  valid_from timestamp [not null]
  valid_to timestamp
  is_current boolean [not null]
  Note: 'Dimension: product master, SCD2, keys-only (text lives in the snowflaked dims)'
}

Table dim_brand {
  brand_key bigint [pk, note: 'Conformed hash of brand']
  brand_name string
}
Table dim_main_category {
  main_category_key bigint [pk, note: 'Conformed hash of main category']
  main_category_name string
}
Table dim_sub_category {
  sub_category_key bigint [pk, note: 'Conformed hash of sub category']
  sub_category_name string
  main_category_key bigint [ref: > dim_main_category.main_category_key, note: 'FK — snowflaked parent']
}

// ---- Geography (snowflaked: country <- region <- geo(city leaf)) ----
Table dim_geo {
  geo_key integer [pk, note: 'City grain (ROW_NUMBER)']
  city string
  region_key bigint [ref: > dim_region.region_key, note: 'FK; NULL when no region parsed']
}
Table dim_region {
  region_key bigint [pk, note: 'Conformed hash of (region, country)']
  region_name string
  country_key bigint [ref: > dim_country.country_key, note: 'FK — snowflaked parent']
}
Table dim_country {
  country_key bigint [pk, note: 'Conformed hash of country']
  country_name string [note: "Constant 'US' at current data scale — thin-data caveat"]
}

// ---- Marketing / device dimensions ----
Table dim_source {
  source_key integer [pk]
  source string [note: 'e.g. google, meta, tiktok']
}
Table dim_medium {
  medium_key integer [pk]
  medium string [note: 'e.g. organic, cpc, social']
  medium_category string [note: 'Organic, Paid Search, Social, Display, ...']
}
Table dim_devices {
  device_key integer [pk]
  device_type string [note: 'Mobile, Desktop, Tablet']
  browser string
  os string
}
Table dim_ad_platform {
  platform_key bigint [pk, note: 'Conformed hash of platform_name']
  platform_name string
  channel_type string [note: 'Paid Social, Search, DSP, ...']
}

// ---- Date ----
Table dim_date {
  date_key integer [pk, note: 'YYYYMMDD']
  date date [unique, not null]
  day_of_week integer
  month integer
  quarter integer
  year integer
  is_weekend boolean
  is_holiday boolean
}

// ---- Facts ----
Table fct_transactions {
  item_id integer [pk, note: 'Grain: one row per unit sold, globally unique (#56)']
  date_key integer [ref: > dim_date.date_key, not null]
  user_crm_id integer [ref: > dim_users.user_crm_id, note: 'NULL for guest checkout']
  user_cookie_id string
  session_id string [ref: > fct_sessions.session_id]
  product_id integer [ref: > dim_products.product_id, not null]
  transaction_id integer [note: 'Natural transaction identifier (repeats across its items)']
  product_price float
  product_quantity integer
  product_revenue float [note: 'price * quantity']
  transaction_revenue float
  transaction_shipping float
  transaction_total float
  transaction_coupon string
  pricing_type string [note: 'Discount | Full Price']
  customer_type string [note: 'Registered | Guest']
  loom_plus_status string
  return_status string
  return_quantity integer
  return_date date
  has_return boolean
  return_rate_pct float
  Note: 'Fact: transaction line items, per-unit grain, with returns + profitability inputs'
}

Table fct_sessions {
  session_id string [pk, note: 'Natural key; unique test at severity: warn']
  date_key integer [ref: > dim_date.date_key, not null]
  user_crm_id integer [ref: > dim_users.user_crm_id]
  user_cookie_id string
  source_key integer [ref: > dim_source.source_key]
  medium_key integer [ref: > dim_medium.medium_key]
  platform_key bigint [ref: > dim_ad_platform.platform_key]
  geo_key integer [ref: > dim_geo.geo_key]
  device_key integer [ref: > dim_devices.device_key]
  page_views integer
  add_to_cart_flag boolean
  bounce_flag boolean
  transaction_count integer
  session_duration_seconds float [note: 'NULL for bounced sessions']
  Note: 'Fact: session-level metrics with attribution + device/geo context'
}

Table fct_advertising {
  ad_key bigint [pk, note: 'Conformed hash of (date, platform_name)']
  date_key integer [ref: > dim_date.date_key, not null]
  platform_key bigint [ref: > dim_ad_platform.platform_key]
  impressions integer
  clicks integer
  cost float
  ctr float [note: 'clicks / impressions']
  Note: 'Fact: daily ad-platform spend and performance'
}

//============================================================================
// MARTS LAYER — business-ready analytics (rpt_)
//============================================================================

Table rpt_transactions {
  item_id integer [pk, note: 'Per-unit line-item grain (from fct_transactions)']
  date_key integer [ref: > dim_date.date_key, not null]
  user_crm_id integer [ref: > dim_users.user_crm_id, note: 'NULL for guest checkout']
  user_cookie_id string
  session_id string
  product_id integer [ref: > dim_products.product_id, not null]
  transaction_date date
  transaction_year integer
  transaction_month integer
  transaction_quarter integer
  transaction_day_of_week integer
  is_weekend boolean
  is_holiday boolean
  product_name string
  product_brand string
  product_main_category string
  product_sub_category string
  product_gender_target string
  product_list_price float
  user_city string
  user_gender string
  user_registration_date date
  user_lifetime_orders integer
  user_lifetime_value float
  user_loom_plus_status boolean
  coupon_flag boolean
  return_status string
  quantity integer
  revenue float [note: 'price * quantity']
  cost float [note: 'unit_cost * quantity']
  gross_profit float [note: 'revenue - cost']
  refund_amount float
  net_revenue float [note: 'revenue - refund_amount']
  Note: 'Mart: line-item transaction analysis with profitability and refunds'
}

Table rpt_customer_activity {
  user_crm_id integer [ref: > dim_users.user_crm_id, not null]
  activity_type string [note: 'profile_change | transaction | session']
  activity_date date [not null]
  activity_timestamp timestamp [not null]
  customer_city string
  customer_gender string
  loom_plus_status boolean
  loom_plus_tier string
  opt_in_status boolean
  lifetime_orders integer
  lifetime_value float
  transaction_id integer [note: 'transaction events only']
  session_id string
  product_id integer [note: 'transaction events only']
  product_revenue float
  product_quantity integer
  customer_state_at_time string [note: 'New | Repeat | Loyal | Premium Customer']
  customer_version_key bigint [note: 'SCD surrogate key for the customer version']
  change_type string
  customer_activity_sequence integer
  customer_tenure_days integer
  Note: 'Mart: SCD-chronology customer journey (profile changes + transactions, PIT customer state)'
}

Table rpt_daily_channel_performance {
  date date [not null]
  channel string [note: 'Paid Social, Search, DSP, ... (dim_ad_platform.channel_type)']
  platform string [note: 'Facebook, Google Ads, TikTok, ...']
  clicks integer
  impressions integer
  ad_spend float
  sessions integer
  total_users integer
  new_users integer
  bounces integer
  page_views integer
  avg_session_duration float
  transaction_count integer
  total_revenue float
  item_quantity integer
  item_price_total float
  Note: 'Mart: daily date x channel x platform KPI aggregation (device not in grain)'
}

//============================================================================
// eBay competitor stand-in (seeded; retired by the eBay ETL, Plan 04)
//============================================================================
// ebay_dim_brand, ebay_dim_category, ebay_fct_items — built from the
// transformed_competitor_data seed; independent of the loom_sync star above.
```

## 🔄 Key improvements over the legacy structure

### 1. Conformed keys, no lookup joins
Surrogate/FK keys are deterministic `FARM_FINGERPRINT` INT64 hashes, so a child model computes the
same key its parent stores. Joins are integer-on-integer and cheap; there are no key-lookup
round-trips. `relationships` tests enforce referential integrity across the star.

### 2. Snowflaked ~3NF core
Two hierarchies are broken out of the wide dimensions to remove repeating text and model the real
grain:
- **Geography**: `dim_country` ← `dim_region` ← `dim_geo` (city leaf), assembled via the ephemeral
  `int_geo_locations`.
- **Product**: `dim_brand` and `dim_main_category` ← `dim_sub_category`, with `dim_products` now
  **keys-only** (`brand_key`, `sub_category_key`). The `rpt_` marts re-join the sub-dims for display
  names.

### 3. SCD Type 2 history
`dim_users` (and `dim_products`) carry `valid_from` / `valid_to` / `is_current`, so facts join
**point-in-time** to the customer/product state as of the event. `rpt_customer_activity` reconstructs
the customer journey from that history.

### 4. Per-unit transaction grain (#56)
`fct_transactions` is one row per **unit sold** with a globally-unique `item_id` (uniqueness tested
at `severity: error`). This distinguishes duplicate products within a transaction — e.g. a partial
return of one of two identical items — which the old `(transaction_id, product_id)` grain could not.

### 5. Integer-first identifiers (#36)
Natural keys are integer and never exposed outside the warehouse, so enumeration is out of the threat
model; integers minimise BigQuery storage and join cost. `session_id` / `user_cookie_id` stay string.

## Layer map

| Layer | Models |
|-------|--------|
| **staging** (views) | `stg_users`, `stg_transactions`, `stg_transactions_and_items`, `stg_sessions`, `stg_product_attributes`, `stg_product_costs`, `stg_product_list_prices`, `stg_product_returns`, `stg_funnel_events`, `stg_adplatform_data`, `stg_adplatform_data_unpivoted` |
| **core dims** | `dim_date`, `dim_users`, `dim_products`, `dim_brand`, `dim_main_category`, `dim_sub_category`, `dim_geo`, `dim_region`, `dim_country`, `dim_source`, `dim_medium`, `dim_devices`, `dim_ad_platform` (+ `ebay_dim_brand`, `ebay_dim_category`) |
| **core facts** | `fct_sessions`, `fct_transactions`, `fct_advertising` (+ `ebay_fct_items`); ephemeral `int_geo_locations` |
| **marts** | `rpt_transactions`, `rpt_customer_activity`, `rpt_daily_channel_performance` |

> For the validated `dbt build` result (PASS/WARN/ERROR counts, accepted warnings, reproduction
> steps) see [dbt-build-summary.md](dbt-build-summary.md).
