# dbt Build Validation Summary

Records the first green end-to-end `dbt build` of the Loom warehouse against Faker-seeded
`dev_loom_sync` data (Plan 03, issues #11–13).

## Result

```
Done. PASS=182 WARN=2 ERROR=0 SKIP=0 NO-OP=0 TOTAL=184
```

- **29 models** (10 staging views + 19 core/mart tables), **155 data tests**, **1 seed**, **11 sources**.
- **0 errors, 0 skips.** The only 2 warnings are intentional (below).

## Layers

| Layer | Contents |
|-------|----------|
| sources | `loom_sync` (10 tables) + `ebay.ebay_transformed` (seeded stand-in) |
| staging | `stg_*` (views): adplatform, funnel events, sessions, transactions(+items), products (attributes/costs/list prices), returns, users |
| core | dims: `dim_date/devices/medium/source/geo/products/users/ad_platform`, `ebay_dim_brand/category`; facts: `fct_sessions/transactions/advertising`, `ebay_fct_items` |
| marts | `rpt_customer_activity`, `rpt_transactions`, `marketing_metrics_mart`, `rpt_daily_channel_performance` |

## Accepted warnings (2)

Both are `severity: warn` by design — the eBay data is *scraped competitor listings* whose
real-world values legitimately exceed the strict enums:

- `ebay_transformed.condition` — 13 rows outside `{New with tags/box, New without tags}`
- `ebay_transformed.gender` — 1 row outside `{mens, womens, unisex, kids}`

These are surfaced (not fatal) intentionally and will be normalized by the eBay ETL (Plan 04).

## Data reconciliation notes

The inherited warehouse **normalizes natural keys to INTEGER** (`SAFE_CAST(<id> AS INTEGER)`),
and `stg_users` additionally filters `LENGTH(user_crm_id) = 7`. The synthetic data generator was
aligned to these assumptions so keys resolve:

| Key | Generated format |
|-----|------------------|
| `item_id` | numeric SKU `100000+` |
| `transaction_id` | numeric `500000000+` |
| `user_crm_id` | numeric, 7-digit `1000000+` |

> These INTEGER casts + the hardcoded length guard are fragile (they'd drop legitimate
> alphanumeric keys). Hardening the warehouse to string-typed natural keys is tracked as tech debt.

## Reproduce

```bash
# prerequisites: terraform applied (Plan 01), data seeded (Plan 02), gcloud ADC as project owner
uv tool install dbt-core --with dbt-bigquery --python 3.12   # dbt lags Python; pin 3.12
set -a && source .env && set +a

dbt deps  --project-dir pipeline/dbt
# eBay landing is both a seed and a source (no dep edge) — seed first, then build excluding it:
dbt seed  --project-dir pipeline/dbt --profiles-dir pipeline/dbt
dbt build --project-dir pipeline/dbt --profiles-dir pipeline/dbt --exclude transformed_competitor_data
```
