"""Orchestrate all generators in dependency order into a dict of DataFrames.

Grown task-by-task; keyed by the exact loom_sync source table names.
"""

from __future__ import annotations

import pandas as pd

from loom_datagen.domain.adspend import build_adspend
from loom_datagen.domain.catalog import build_catalog
from loom_datagen.domain.events import build_funnelevents, build_returns
from loom_datagen.domain.sessions import build_sessions
from loom_datagen.domain.transactions import build_transactions
from loom_datagen.domain.users import build_users
from loom_datagen.infrastructure.rng import make_faker, make_rng
from loom_datagen.validation.contracts import validate_frames


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

    frames = {
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

    validate_frames(frames)

    return frames
