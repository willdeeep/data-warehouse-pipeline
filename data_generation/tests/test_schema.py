"""Schema guards: every loom_sync column carries a BigQuery description (#25)."""

from __future__ import annotations

from loom_datagen.schema import SCHEMAS


def test_every_column_has_a_nonempty_description():
    missing = [
        f"{table}.{field.name}"
        for table, fields in SCHEMAS.items()
        for field in fields
        if not (field.description or "").strip()
    ]
    assert not missing, f"source columns missing a description: {missing}"


def test_all_ten_source_tables_present():
    assert len(SCHEMAS) == 10
