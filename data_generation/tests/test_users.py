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
