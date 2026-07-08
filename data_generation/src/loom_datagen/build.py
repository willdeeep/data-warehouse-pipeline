"""Orchestrate all generators in dependency order into a dict of DataFrames.

Grown task-by-task; keyed by the exact loom_sync source table names.
"""
from __future__ import annotations

import pandas as pd

from .catalog import build_catalog
from .rng import make_faker, make_rng
from .sessions import build_sessions
from .users import build_users


def build_all(cfg) -> dict[str, pd.DataFrame]:
    rng = make_rng(cfg.seed)
    fake = make_faker(cfg.seed)

    attrs, costs, prices = build_catalog(cfg, rng, fake)
    users = build_users(cfg, rng, fake)
    sessions = build_sessions(cfg, rng, fake, users)

    return {
        "productattributes": attrs,
        "product_costs": costs,
        "product_listprices": prices,
        "users": users,
        "sessions": sessions,
    }
