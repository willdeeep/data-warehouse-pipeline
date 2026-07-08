"""Orchestrate all generators in dependency order into a dict of DataFrames.

Grown task-by-task; keyed by the exact loom_sync source table names.
"""
from __future__ import annotations

import pandas as pd

from .catalog import build_catalog
from .rng import make_faker, make_rng


def build_all(cfg) -> dict[str, pd.DataFrame]:
    rng = make_rng(cfg.seed)
    fake = make_faker(cfg.seed)

    attrs, costs, prices = build_catalog(cfg, rng, fake)

    return {
        "productattributes": attrs,
        "product_costs": costs,
        "product_listprices": prices,
    }
