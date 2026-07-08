"""Users generator: one customer profile per user_crm_id."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_users(cfg, rng: np.random.Generator, fake) -> pd.DataFrame:
    n = cfg.n_users
    crm = [f"CRM-{i:07d}" for i in range(n)]

    reg = pd.to_datetime(cfg.start_date) + pd.to_timedelta(rng.integers(0, 900, n), unit="D")

    subscribed = rng.random(n) < 0.25
    tier = pd.Series([pd.NA] * n, dtype="object")
    tier[subscribed] = rng.choice(["Silver", "Gold", "Platinum"], int(subscribed.sum()))

    return pd.DataFrame({
        "user_crm_id": crm,
        "city": [fake.city() for _ in range(n)],
        "first_purchase_date": (reg + pd.to_timedelta(rng.integers(0, 60, n), unit="D")).date,
        "latest_login_date": (reg + pd.to_timedelta(rng.integers(60, 400, n), unit="D")).date,
        "latest_purchase_date": (reg + pd.to_timedelta(rng.integers(30, 300, n), unit="D")).date,
        "opt_in_status": rng.random(n) < 0.6,
        "loom_plus_status": subscribed,
        "loom_plus_tier": tier,
        "registration_date": reg.date,
        "user_gender": rng.choice(
            ["M", "F", "Non-binary", "Unknown"], n, p=[0.45, 0.45, 0.05, 0.05]
        ),
    })
