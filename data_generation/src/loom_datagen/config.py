"""Configuration for the synthetic data generator (env + optional scale presets)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatagenConfig(BaseSettings):
    """Runtime configuration. Env vars are prefixed LOOM_ (e.g. LOOM_PROJECT_ID)."""

    model_config = SettingsConfigDict(env_prefix="LOOM_", env_file=".env", extra="ignore")

    # BigQuery target
    project_id: str
    source_dataset: str = "loom_sync"
    bq_location: str = "US"

    # Generation controls
    seed: int = 42
    n_products: int = 500
    n_users: int = 2000
    start_date: str = "2023-01-01"
    end_date: str = "2024-12-31"
    avg_sessions_per_day: int = 400
    conversion_rate: float = 0.03
