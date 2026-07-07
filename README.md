# Loom — Data Warehouse Pipeline

A portfolio data-engineering project: a synthetic e-commerce analytics warehouse for
**Loom** (a fictional online fashion retailer), built to be **run end-to-end by anyone**
with a GCP project.

Terraform provisions the platform, a standalone Faker generator seeds realistic source data
into BigQuery, a small ETL lands competitor (eBay) data, and **dbt** builds the warehouse in
staging → intermediate → marts layers.

> 🚧 **Status:** active rebuild. The full "run it yourself" guide, architecture diagrams, and
> ERD land in the docs polish phase. Until then, the roadmap and detailed plans live in
> `.opencode/plans/` (untracked).

## Stack

- **IaC:** Terraform (BigQuery, IAM, GCS) — auth via `gcloud` OAuth2 / ADC
- **Data generation:** Python 3.13, `uv`, Faker → BigQuery (one-time seeder)
- **Warehouse:** dbt + BigQuery (staging / intermediate / marts)
- **Ingestion:** Python ETL (eBay competitor data) on Airflow
- **Quality:** dbt tests, pytest, ruff, pre-commit, GitHub Actions

## Layout

| Path | Purpose |
|------|---------|
| `infra/` | Terraform EAC — provisions the GCP data platform (not containerised) |
| `data_generation/` | Standalone Faker seeder — run once, post-Terraform (not part of the pipeline) |
| `pipeline/` | Containerised dbt warehouse + eBay ETL + Airflow DAGs |
| `docs/` | Architecture, ERD, and ADRs |

## Development

```bash
uv sync                 # root tooling (Python 3.13)
uvx ruff check .        # lint
```

See `.opencode/plans/00-roadmap.md` for the build roadmap.
