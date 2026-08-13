"""Transactions + line items: converting sessions become orders (FK to sessions, products)."""

from __future__ import annotations

import numpy as np
import pandas as pd

_COUPONS = [None, "SAVE10", "FREESHIP", "WELCOME"]
_COUPON_P = [0.70, 0.10, 0.10, 0.10]
_SHIPPING_OPTIONS = [0.0, 4.99, 9.99]


def build_transactions(cfg, rng: np.random.Generator, sessions: pd.DataFrame, prices: pd.DataFrame):
    """Return (transactions_header, transactions_and_items) sharing transaction_id + date."""
    conv = sessions.sample(frac=cfg.conversion_rate, random_state=cfg.seed).reset_index(drop=True)

    price_lookup = prices.set_index("item_id")["item_list_price"]
    item_ids = price_lookup.index.to_numpy()

    headers: list[dict] = []
    lines: list[dict] = []
    item_seq = 0  # global counter -> unique, numeric-castable per-item item_id

    for i, (_, sess) in enumerate(conv.iterrows()):
        # Numeric transaction ids: the warehouse casts transaction_id -> INTEGER.
        txn_id = str(500_000_000 + i)
        k = int(rng.integers(1, 6))
        chosen = rng.choice(item_ids, k, replace=False)
        qtys = rng.integers(1, 4, k)
        sel_prices = price_lookup.loc[chosen].to_numpy()

        revenue = float((sel_prices * qtys).sum())
        shipping = float(rng.choice(_SHIPPING_OPTIONS))
        coupon = _COUPONS[int(rng.choice(len(_COUPONS), p=_COUPON_P))]

        # Explode each (product, quantity) into one row per unit sold, each with its own item_id so
        # two units of the same product are distinguishable (e.g. a partial return).
        for prod, q, p in zip(chosen, qtys, sel_prices, strict=True):
            for _ in range(int(q)):
                lines.append(
                    {
                        "item_id": str(900_000_000 + item_seq),
                        "transaction_id": txn_id,
                        "product_id": prod,
                        "date": sess["date"],
                        "item_price": round(float(p), 2),
                        "item_quantity": 1,
                    }
                )
                item_seq += 1

        headers.append(
            {
                "transaction_id": txn_id,
                "date": sess["date"],
                "session_id": sess["session_id"],
                "transaction_coupon": coupon,
                "transaction_revenue": round(revenue, 2),
                "transaction_shipping": shipping,
                "transaction_total": round(revenue + shipping, 2),
                "user_cookie_id": sess["user_cookie_id"],
                "user_crm_id": sess["user_crm_id"],
            }
        )

    return pd.DataFrame(headers), pd.DataFrame(lines)
