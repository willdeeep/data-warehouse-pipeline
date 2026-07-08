"""Sessions generator: one row per session, ~70% tied to a known user (FK to users)."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRAFFIC_MEDIUMS = [
    "organic", "paid", "email", "social", "direct", "referral", "cpc", "display",
    "(none)", "crm", "affiliate", "influencer", "cpm", "organic_social",
    "paid_social", "comparison", "cpv",
]

TRAFFIC_SOURCES = ["google", "facebook", "direct", "instagram", "tiktok", "newsletter"]


_HEX = np.array(list("0123456789abcdef"))


def _hex_ids(rng: np.random.Generator, n: int, prefix: str, width: int) -> list[str]:
    """Random ids of exactly `width` hex chars, drawn digit-by-digit (avoids int overflow)."""
    digits = _HEX[rng.integers(0, 16, size=(n, width))]
    return [prefix + "".join(row) for row in digits]


def build_sessions(cfg, rng: np.random.Generator, fake, users: pd.DataFrame) -> pd.DataFrame:
    days = pd.date_range(cfg.start_date, cfg.end_date, freq="D")
    n = len(days) * cfg.avg_sessions_per_day

    dates = rng.choice(days, n)
    logged_in = rng.random(n) < 0.7
    crm = pd.Series([pd.NA] * n, dtype="object")
    crm[logged_in] = rng.choice(users["user_crm_id"].to_numpy(), int(logged_in.sum()))

    return pd.DataFrame({
        "session_id": _hex_ids(rng, n, "SESS-", 12),
        "date": pd.to_datetime(dates).date,
        "city": [fake.city() for _ in range(n)],
        "device_category": rng.choice(
            ["desktop", "mobile", "tablet", "unknown"], n, p=[0.45, 0.45, 0.08, 0.02]
        ),
        "traffic_medium": rng.choice(TRAFFIC_MEDIUMS, n),
        "traffic_source": rng.choice(TRAFFIC_SOURCES, n),
        "user_cookie_id": _hex_ids(rng, n, "CK-", 16),
        "user_crm_id": crm,
    })
