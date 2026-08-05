import pandas as pd


def test_users_constraints(frames):
    u = frames["users"]
    assert u["user_crm_id"].notna().all()
    assert u["user_gender"].isin(["M", "F", "Non-binary", "Unknown"]).all()
    assert u["loom_plus_status"].dtype == bool
    assert (pd.to_datetime(u["registration_date"]) >= pd.Timestamp("2020-01-01")).all()
    # tier only set when subscribed
    assert u.loc[~u["loom_plus_status"], "loom_plus_tier"].isna().all()
    assert u.loc[u["loom_plus_status"], "loom_plus_tier"].notna().all()


def test_users_have_scd2_history(frames):
    u = frames["users"]
    per_user = u.groupby("user_crm_id").size()
    multi = per_user[per_user > 1]
    assert len(multi) > 0, "no user has version history"
    share = len(multi) / per_user.shape[0]
    assert 0.20 <= share <= 0.50, f"multi-version share {share:.2f} outside 0.20-0.50"
    assert (per_user <= 3).all(), "no user should exceed 3 versions (1 current + <=2 prior)"


def test_users_versions_are_ordered_and_changing(frames):
    u = frames["users"].copy()
    u["valid_from"] = pd.to_datetime(u["valid_from"])
    tracked = ["city", "user_gender", "opt_in_status", "loom_plus_status", "loom_plus_tier"]
    for crm, g in u.groupby("user_crm_id"):
        g = g.sort_values("valid_from")
        assert g["valid_from"].is_unique, f"duplicate valid_from for {crm}"
        assert g["valid_from"].is_monotonic_increasing
        if len(g) > 1:
            changed = (g[tracked].ne(g[tracked].shift())).iloc[1:].any(axis=1)
            assert changed.all(), f"a version of {crm} changed no tracked attribute"


def test_users_valid_from_not_null(frames):
    u = frames["users"]
    assert u["valid_from"].notna().all()
