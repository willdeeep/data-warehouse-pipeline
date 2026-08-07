# System Overview & Data Flow

The Loom warehouse is a portfolio data platform: synthetic source data lands in BigQuery, dbt
transforms it through a layered dimensional model, and the `rpt_` marts serve analytics. All
infrastructure is Terraform-provisioned; CI/CD runs on GitHub Actions.

> Companion docs: [erd.md](erd.md) (entity-relationship model), [dbt-build-summary.md](dbt-build-summary.md)
> (validated build state), [RELEASE.md](../RELEASE.md) (branch/env + deployment model).

## System architecture

```mermaid
flowchart LR
    subgraph gen["Data generation"]
        faker["loom-datagen<br/>(Faker, seed=42)"]
        ebay["eBay seed<br/>(competitor stand-in)"]
    end

    subgraph gcp["BigQuery"]
        src[("loom_sync<br/>source dataset")]
        wh[("warehouse<br/>dataset")]
    end

    subgraph dbt["dbt transform"]
        stg["staging<br/>(views)"]
        core["core<br/>(dims + facts,<br/>snowflaked, SCD2)"]
        marts["marts<br/>(rpt_)"]
    end

    bi["BI / analytics<br/>(dashboards, ad-hoc SQL)"]

    faker -->|"validate + load"| src
    ebay -->|"dbt seed"| wh
    src -->|"sources"| stg
    stg --> core --> marts
    marts --> bi
    stg --- wh
    core --- wh
    marts --- wh

    subgraph platform["Platform (Terraform)"]
        tf["BQ datasets · GCS buckets<br/>IAM · WIF (keyless CI)"]
    end
    tf -.provisions.-> gcp

    subgraph cicd["CI/CD (GitHub Actions)"]
        ci["ci.yml<br/>lint · datagen tests · tf validate"]
        deploy["deploy-main.yml<br/>WIF → terraform apply (prod)"]
    end
    ci -.gates.-> dbt
    deploy -.applies.-> tf

    orch["Orchestration<br/>(Airflow — deferred, Plan 06)"]:::deferred
    orch -.will run.-> faker
    orch -.will run.-> dbt

    classDef deferred stroke-dasharray: 4 4,opacity:0.7;
```

Datasets are environment-prefixed in a single GCP project — `dev_loom_sync`/`dev_warehouse`,
`stg_*`, and bare `loom_sync`/`warehouse` for prod (see [RELEASE.md](../RELEASE.md)).

## dbt lineage (layers)

```mermaid
flowchart TD
    subgraph S["staging (views)"]
        s_users["stg_users"]
        s_txn["stg_transactions"]
        s_items["stg_transactions_and_items"]
        s_sess["stg_sessions"]
        s_prod["stg_product_attributes<br/>+ costs / list_prices / returns"]
        s_funnel["stg_funnel_events"]
        s_ads["stg_adplatform_data<br/>(+ unpivoted)"]
    end

    subgraph C["core (dims + facts)"]
        d_users["dim_users (SCD2)"]
        d_prod["dim_products (SCD2, keys-only)"]
        d_geo["dim_country ← dim_region ← dim_geo"]
        d_pcat["dim_brand · dim_main_category ← dim_sub_category"]
        d_misc["dim_date · dim_source · dim_medium<br/>dim_devices · dim_ad_platform"]
        f_txn["fct_transactions<br/>(grain: item_id)"]
        f_sess["fct_sessions"]
        f_ads["fct_advertising"]
    end

    subgraph M["marts (rpt_)"]
        r_txn["rpt_transactions"]
        r_act["rpt_customer_activity"]
        r_chan["rpt_daily_channel_performance"]
    end

    s_users --> d_users
    s_prod --> d_prod
    s_prod --> d_pcat
    s_sess --> d_geo
    s_sess --> f_sess
    s_txn --> f_txn
    s_items --> f_txn
    s_funnel --> f_sess
    s_ads --> f_ads

    d_users --> f_txn
    d_prod --> f_txn
    d_geo --> f_sess
    d_misc --> f_sess

    f_txn --> r_txn
    d_users --> r_act
    f_txn --> r_act
    f_sess --> r_act
    f_ads --> r_chan
    f_sess --> r_chan
    f_txn --> r_chan
```

## Warehouse layer catalog

Canonical model inventory (34 models + 1 seed). This is the catalog #24 referred to; the
per-layer summaries in [erd.md](erd.md) and [dbt-build-summary.md](dbt-build-summary.md) defer to
it.

| Layer | Materialization | Models |
|-------|-----------------|--------|
| **staging** | view | `stg_users`, `stg_transactions`, `stg_transactions_and_items`, `stg_sessions`, `stg_product_attributes`, `stg_product_costs`, `stg_product_list_prices`, `stg_product_returns`, `stg_funnel_events`, `stg_adplatform_data`, `stg_adplatform_data_unpivoted` (11) |
| **core — dims** | table | `dim_date`, `dim_users`, `dim_products`, `dim_brand`, `dim_main_category`, `dim_sub_category`, `dim_geo`, `dim_region`, `dim_country`, `dim_source`, `dim_medium`, `dim_devices`, `dim_ad_platform` (13) |
| **core — facts** | table | `fct_sessions`, `fct_transactions`, `fct_advertising` (3) |
| **core — intermediate** | ephemeral | `int_geo_locations` (1) |
| **marts** | table | `rpt_transactions`, `rpt_customer_activity`, `rpt_daily_channel_performance` (3) |
| **eBay stand-in** | table | `ebay_dim_brand`, `ebay_dim_category`, `ebay_fct_items` (3; from the `transformed_competitor_data` seed, retired by the eBay ETL — Plan 04 / v0.4.0) |

## Roadmap context

| Milestone | Theme |
|-----------|-------|
| **v0.2.0** | Conformed dimensional warehouse (this release) |
| **v0.3.0** | Fitness & data contracts (dbt-checkpoint/bouncer, pandera, project-evaluator) |
| **v0.4.0** | eBay ETL — runtime-agnostic package, swappable source |
| **v0.5.0** | Orchestration runtime — spike, ADR, provision + deploy |
