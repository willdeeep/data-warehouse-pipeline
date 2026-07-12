# Loom dbt project

Builds the warehouse from `loom_sync` source data (Faker-seeded) into staging →
intermediate → marts. BigQuery, OAuth/ADC auth, env-prefixed datasets (#29).

## Local setup

dbt's CLI ships in `dbt-core`; the BigQuery adapter is a separate package. dbt lags new
Python releases, so pin its runtime to **3.12** (independent of the repo's 3.13/3.14):

```bash
uv tool install dbt-core --with dbt-bigquery --python 3.12
dbt --version        # dbt-core 1.11.x, bigquery adapter 1.11.x
```

## Running (from the repo root)

Auth once (`gcloud auth application-default login`), then load config and pass the dbt dirs
explicitly (the repo `.env` carries container paths for `DBT_PROFILES_DIR`, so `--profiles-dir`
must override them for local runs):

```bash
set -a && source .env && set +a       # GCP_PROJECT_ID, BQ_LOCATION, DBT_*_DATASET

dbt deps  --project-dir pipeline/dbt
dbt debug --project-dir pipeline/dbt --profiles-dir pipeline/dbt

# Seed first, then build excluding the seed node. The eBay landing table is BOTH a
# seed and a declared source, and dbt has no seed->source dependency edge — seeding
# separately (and excluding it from build) avoids a race where source tests run
# before the table exists. (Goes away once Plan 04's ETL supplies ebay_transformed.)
dbt seed  --project-dir pipeline/dbt --profiles-dir pipeline/dbt
dbt build --project-dir pipeline/dbt --profiles-dir pipeline/dbt --exclude transformed_competitor_data
```

## Datasets (env-prefixed, #29)

| Env | Source (`DBT_SOURCE_DATASET`) | Target (`DBT_WAREHOUSE_DATASET`) |
|-----|-------------------------------|----------------------------------|
| dev | `dev_loom_sync` | `dev_warehouse` |
| staging | `stg_loom_sync` | `stg_warehouse` |
| prod | `loom_sync` | `warehouse` |

The eBay competitor landing table (`ebay_transformed`) is seeded from
`seeds/transformed_competitor_data.csv` into the target dataset until the Plan 04 ETL
supplies it live.
