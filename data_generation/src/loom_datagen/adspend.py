"""Ad-platform daily spend generator: one row per date, five channels."""

from __future__ import annotations

import numpy as np
import pandas as pd

# channel -> (avg daily impressions, click-through rate, cost-per-click USD)
_CHANNELS = {
    "criteo": (20_000, 0.010, 0.45),
    "google": (50_000, 0.030, 0.80),
    "meta": (40_000, 0.020, 0.65),
    "rtbhouse": (15_000, 0.008, 0.40),
    "tiktok": (30_000, 0.015, 0.55),
}


def build_adspend(cfg, rng: np.random.Generator) -> pd.DataFrame:
    days = pd.date_range(cfg.start_date, cfg.end_date, freq="D")
    n = len(days)

    data: dict[str, object] = {"date": days.date}
    for ch, (avg_impr, ctr, cpc) in _CHANNELS.items():
        impressions = rng.poisson(avg_impr, n)
        clicks = rng.binomial(impressions, ctr)
        cost = (clicks * cpc * rng.uniform(0.8, 1.2, n)).round(2)
        data[f"{ch}_clicks"] = clicks
        data[f"{ch}_cost"] = cost
        data[f"{ch}_impressions"] = impressions

    return pd.DataFrame(data)
