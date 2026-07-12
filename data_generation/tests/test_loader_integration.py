"""Integration smoke test — requires a real GCP project + ADC. Skipped by default."""

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("LOOM_PROJECT_ID"), reason="needs real project + ADC")
def test_load_and_validate_roundtrip():
    from loom_datagen.build import build_all
    from loom_datagen.config import DatagenConfig
    from loom_datagen.loader import load_frames
    from loom_datagen.validate import validate_bigquery

    cfg = DatagenConfig(
        n_products=20,
        n_users=50,
        start_date="2024-01-01",
        end_date="2024-01-31",
        avg_sessions_per_day=20,
    )
    counts = load_frames(build_all(cfg), cfg)
    assert counts["users"] == 50

    report = validate_bigquery(cfg)
    assert report["orphans"] == 0
    assert report["violations"] == []
