"""Orchestrate all generators in dependency order into a dict of DataFrames.

Grown task-by-task; keyed by the exact loom_sync source table names.
"""

from __future__ import annotations

import pandas as pd

from .adspend import build_adspend
from .catalog import build_catalog
from .events import build_funnelevents, build_returns
from .rng import make_faker, make_rng
from .sessions import build_sessions
from .transactions import build_transactions
from .users import build_users


def build_all(cfg) -> dict[str, pd.DataFrame]:
    rng = make_rng(cfg.seed)
    fake = make_faker(cfg.seed)

    attrs, costs, prices = build_catalog(cfg, rng, fake)
    users = build_users(cfg, rng, fake)
    sessions = build_sessions(cfg, rng, fake, users)
    txns, items = build_transactions(cfg, rng, sessions, prices)
    funnelevents = build_funnelevents(cfg, rng, sessions, attrs, txns)
    returns = build_returns(cfg, rng, items)
    adspend = build_adspend(cfg, rng)

    return {
        "productattributes": attrs,
        "product_costs": costs,
        "product_listprices": prices,
        "users": users,
        "sessions": sessions,
        "transactions": txns,
        "transactionsanditems": items,
        "funnelevents": funnelevents,
        "product_returns": returns,
        "adplatform_data": adspend,
    }
