"""Users generator: SCD2 profile history — one row per user_crm_id per version."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Fraction of users given profile history, and tracked attributes that may change across versions.
_HISTORY_SHARE = 0.35
_TRACKED = ["city", "user_gender", "opt_in_status", "loom_plus_status", "loom_plus_tier"]
_GUARANTEED_FLIP = ["opt_in_status", "loom_plus_status"]  # booleans: toggling always changes them


def _tier_for(status: bool, rng: np.random.Generator):
    """Loom+ tier is set iff subscribed (preserves the test_users invariant)."""
    return rng.choice(["Silver", "Gold", "Platinum"]) if status else pd.NA


def build_users(cfg, rng: np.random.Generator, fake) -> pd.DataFrame:
    n = cfg.n_users
    # Numeric, exactly-7-digit CRM ids: the warehouse casts user_crm_id -> INTEGER and
    # stg_users filters `LENGTH(...) = 7`, so 6-digit ids get silently dropped (empty dim_users).
    crm = [str(1_000_000 + i) for i in range(n)]

    reg = pd.to_datetime(cfg.start_date) + pd.to_timedelta(rng.integers(0, 900, n), unit="D")

    subscribed = rng.random(n) < 0.25
    tier = pd.Series([pd.NA] * n, dtype="object")
    tier[subscribed] = rng.choice(["Silver", "Gold", "Platinum"], int(subscribed.sum()))

    # The CURRENT (latest) version of every user — same distributions as before.
    current = pd.DataFrame(
        {
            "user_crm_id": crm,
            "city": [fake.city() for _ in range(n)],
            "first_purchase_date": (reg + pd.to_timedelta(rng.integers(0, 60, n), unit="D")).date,
            "latest_login_date": (reg + pd.to_timedelta(rng.integers(60, 400, n), unit="D")).date,
            "latest_purchase_date": (
                reg + pd.to_timedelta(rng.integers(30, 300, n), unit="D")
            ).date,
            "opt_in_status": rng.random(n) < 0.6,
            "loom_plus_status": subscribed,
            "loom_plus_tier": tier,
            "registration_date": reg.date,
            "user_gender": rng.choice(
                ["M", "F", "Non-binary", "Unknown"], n, p=[0.45, 0.45, 0.05, 0.05]
            ),
        }
    )

    genders = ["M", "F", "Non-binary", "Unknown"]
    rows = []
    for i in range(n):
        cur = current.iloc[i].to_dict()
        reg_ts = pd.Timestamp(reg[i])

        if rng.random() < _HISTORY_SHARE:
            n_prior = int(rng.integers(1, 3))  # 1 or 2 prior versions
        else:
            n_prior = 0

        # valid_from dates: n_prior earlier dates + the current version's own effective date,
        # all strictly after registration, sorted ascending.
        span_days = max((pd.Timestamp(cfg.end_date) - reg_ts).days, n_prior + 2)
        offsets = sorted(
            int(o) for o in rng.choice(np.arange(1, span_days), size=n_prior + 1, replace=False)
        )
        version_dates = [reg_ts + pd.Timedelta(days=o) for o in offsets]

        # Work backwards from current attributes, mutating tracked fields for each prior version.
        # Each prior version must differ from the version immediately newer than it in >=1 tracked
        # attribute. To make that deterministic (not just "usually true"), every mutation always
        # includes one guaranteed-flip boolean attribute, plus optionally a second random one.
        chain = [dict(cur)]
        for _ in range(n_prior):
            prev = dict(chain[0])  # copy the currently-oldest-known state, then perturb it
            flip_attr = _GUARANTEED_FLIP[int(rng.integers(0, len(_GUARANTEED_FLIP)))]
            attrs_to_change = [flip_attr]
            if rng.random() < 0.5:
                extra_pool = [a for a in _TRACKED if a != flip_attr]
                attrs_to_change.append(extra_pool[int(rng.integers(0, len(extra_pool)))])

            for attr in attrs_to_change:
                if attr == "city":
                    prev["city"] = fake.city()
                elif attr == "user_gender":
                    prev["user_gender"] = genders[int(rng.integers(0, len(genders)))]
                elif attr == "opt_in_status":
                    prev["opt_in_status"] = not prev["opt_in_status"]
                elif attr == "loom_plus_status":
                    prev["loom_plus_status"] = not prev["loom_plus_status"]
                    prev["loom_plus_tier"] = _tier_for(prev["loom_plus_status"], rng)
                elif attr == "loom_plus_tier":
                    if prev["loom_plus_status"]:
                        prev["loom_plus_tier"] = _tier_for(True, rng)
            if not prev["loom_plus_status"]:
                prev["loom_plus_tier"] = pd.NA
            chain.insert(0, prev)  # prepend: older state

        for row, vf in zip(chain, version_dates, strict=True):
            row = dict(row)
            row["valid_from"] = vf.date()
            rows.append(row)

    out = pd.DataFrame(rows)
    return out.sort_values(["user_crm_id", "valid_from"]).reset_index(drop=True)
