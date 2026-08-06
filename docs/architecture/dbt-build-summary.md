# dbt Build Validation Summary

Records the green end-to-end `dbt build` of the Loom warehouse against Faker-seeded
`dev_loom_sync` data. Baseline established in Plan 03 (issues #11–13); refreshed after
Plan 09 (layer/naming restructure + marts cleanup) and Plan 13 (real SCD2 history for `dim_users`).

## Result

```
Done. PASS=182 WARN=4 ERROR=0 SKIP=0 NO-OP=0 TOTAL=186
```

- **28 models** (10 staging views + 18 core/mart tables), **1 seed**, **11 sources**.
- **0 errors, 0 skips.** All 4 warnings are intentional (below).

> Plan 13 gave `dim_users` genuine SCD Type 2 history: the generator now emits versioned user
> profiles (`valid_from` per version), so `dim_users` carries **749 rows across 500 users** (249
> historical, exactly one `is_current` per user). `rpt_customer_activity` now populates both
> `profile_change` (249) and `transaction` (54) rows — its guard test passes at `severity: error`,
> and the point-in-time join resolves every kept transaction (`pit_violations = 0`).

## Layers

| Layer | Contents |
|-------|----------|
| sources | `loom_sync` (10 tables) + `ebay.ebay_transformed` (seeded stand-in) |
| staging | `stg_*` (views): adplatform, funnel events, sessions, transactions(+items), products (attributes/costs/list prices), returns, users |
| core | dims: `dim_date/devices/medium/source/geo/products/users/ad_platform`, `ebay_dim_brand/category`; facts: `fct_sessions/transactions/advertising`, `ebay_fct_items` |
| marts | `rpt_customer_activity`, `rpt_transactions`, `rpt_daily_channel_performance` |

## Accepted warnings (4)

All are `severity: warn` by design:

- `ebay_transformed.condition` — 13 rows outside `{New with tags/box, New without tags}` (scraped
  competitor listings legitimately exceed the strict enum; normalized by the eBay ETL, Plan 04).
- `ebay_transformed.gender` — 1 row outside `{mens, womens, unisex, kids}` (same reason).
- `unique_fct_transactions_transaction_product_id` and `unique_rpt_transactions_transaction_product_id`
  — `(transaction_id, product_id)` is not unique in the Faker data (a transaction can carry the same
  product on multiple line items). Downgraded to `warn` in #e9c6992; a true composite grain key is
  natural-key-hardening work (#36). These surface/vary with each data regeneration.

## Known data-realism gap (not a warning, but worth noting)

`rpt_customer_activity` keeps **54 of 789** fact-transaction rows: the other **735 transactions are
dated *before* their user's `registration_date`**, so the mart's (correct) point-in-time join
excludes them — you can't attribute a purchase to a customer profile that didn't exist yet. The root
cause is upstream: the generator samples session/transaction dates across the whole calendar range
without bounding them to `>= registration_date`. Constraining session dates to a user's post-signup
window is a follow-up datagen improvement (does not affect SCD2 correctness).

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
