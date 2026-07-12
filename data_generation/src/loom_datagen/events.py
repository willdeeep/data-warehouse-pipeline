"""Funnel events + product returns (FK to sessions, products, transactions)."""

from __future__ import annotations

import numpy as np
import pandas as pd

EVENTS = [
    "page_view",
    "view_item",
    "add_to_cart",
    "begin_checkout",
    "purchase",
    "remove_from_cart",
]

# Ordered funnel; a session progresses down it until it drops off (or converts).
_FUNNEL = ["page_view", "view_item", "add_to_cart", "begin_checkout"]
_STEP_CONTINUE_P = 0.55  # chance of advancing to the next funnel step (non-converting sessions)


def build_funnelevents(cfg, rng, sessions: pd.DataFrame, attrs: pd.DataFrame, txns: pd.DataFrame):
    item_ids = attrs["item_id"].to_numpy()
    txn_by_session = dict(zip(txns["session_id"], txns["transaction_id"], strict=True))

    rows: list[dict] = []
    for s in sessions.itertuples(index=False):
        sid = s.session_id
        converted = sid in txn_by_session
        base = pd.Timestamp(s.date) + pd.Timedelta(seconds=int(rng.integers(0, 86_400)))

        if converted:
            steps = list(_FUNNEL) + ["purchase"]
        else:
            steps = ["page_view"]
            for nxt in _FUNNEL[1:]:
                if rng.random() < _STEP_CONTINUE_P:
                    steps.append(nxt)
                else:
                    break
            # occasional cart abandonment signal
            if "add_to_cart" in steps and rng.random() < 0.15:
                steps.append("remove_from_cart")

        for i, event in enumerate(steps):
            is_purchase = event == "purchase"
            rows.append(
                {
                    "date": s.date,
                    "device_category": s.device_category,
                    "event_name": event,
                    "event_time": base + pd.Timedelta(seconds=30 * i),
                    "item_id": None if event == "page_view" else rng.choice(item_ids),
                    "session_id": sid,
                    "transaction_id": txn_by_session[sid] if is_purchase else None,
                    "user_cookie_id": s.user_cookie_id,
                    "user_crm_id": s.user_crm_id,
                }
            )

    df = pd.DataFrame(rows)
    df["event_time"] = pd.to_datetime(df["event_time"])
    return df


def build_returns(cfg, rng, items: pd.DataFrame) -> pd.DataFrame:
    if len(items) == 0:
        return pd.DataFrame(
            columns=[
                "return_date",
                "transaction_id",
                "item_id",
                "item_quantity",
                "return_quantity",
                "return_status",
            ]
        )

    sample = items.sample(frac=0.05, random_state=cfg.seed).reset_index(drop=True)
    n = len(sample)

    item_qty = sample["item_quantity"].to_numpy()
    return_qty = np.array([int(rng.integers(1, q + 1)) for q in item_qty], dtype=float)
    offsets = rng.integers(1, 31, n)
    return_date = (pd.to_datetime(sample["date"]) + pd.to_timedelta(offsets, unit="D")).dt.date

    return pd.DataFrame(
        {
            "return_date": return_date,
            "transaction_id": sample["transaction_id"].to_numpy(),
            "item_id": sample["item_id"].to_numpy(),
            "item_quantity": item_qty,
            "return_quantity": return_qty,
            "return_status": rng.choice(["Refund", "Exchange"], n, p=[0.7, 0.3]),
        }
    )
