"""Sessions generator: one row per session, ~70% tied to a known user (FK to users)."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRAFFIC_MEDIUMS = [
    "organic",
    "paid",
    "email",
    "social",
    "direct",
    "referral",
    "cpc",
    "display",
    "(none)",
    "crm",
    "affiliate",
    "influencer",
    "cpm",
    "organic_social",
    "paid_social",
    "comparison",
    "cpv",
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

    start = pd.Timestamp(cfg.start_date)
    window_days = (pd.Timestamp(cfg.end_date) - start).days

    logged_in = rng.random(n) < 0.7

    # Baseline: every session gets a uniform random date (as a day-offset) across the window.
    date_off = rng.integers(0, window_days + 1, n)

    crm = pd.Series([pd.NA] * n, dtype="object")
    # users may have multiple SCD2 version rows per user_crm_id; use distinct ids (registration is
    # constant across a user's versions) so multi-version users aren't over-weighted.
    reg_by_user = users.drop_duplicates("user_crm_id").set_index("user_crm_id")["registration_date"]
    n_in = int(logged_in.sum())
    assigned = rng.choice(reg_by_user.index.to_numpy(), n_in)
    crm[logged_in] = assigned

    # Logged-in sessions can't predate signup: resample each date uniformly in
    # [max(registration_date, window_start), window_end]. Transactions inherit session dates, so
    # this bounds them too (#55).
    reg = pd.to_datetime(pd.Series(reg_by_user.loc[assigned].to_numpy()))
    lo_off = (reg - start).dt.days.clip(lower=0).to_numpy()
    span = np.maximum(window_days - lo_off, 0)
    date_off[logged_in] = lo_off + np.floor(rng.random(n_in) * (span + 1)).astype(int)

    dates = start + pd.to_timedelta(date_off, unit="D")

    return pd.DataFrame(
        {
            "session_id": _hex_ids(rng, n, "SESS-", 12),
            "date": dates.date,
            "city": [fake.city() for _ in range(n)],
            "device_category": rng.choice(
                ["desktop", "mobile", "tablet", "unknown"], n, p=[0.45, 0.45, 0.08, 0.02]
            ),
            "traffic_medium": rng.choice(TRAFFIC_MEDIUMS, n),
            "traffic_source": rng.choice(TRAFFIC_SOURCES, n),
            "user_cookie_id": _hex_ids(rng, n, "CK-", 16),
            "user_crm_id": crm,
        }
    )
