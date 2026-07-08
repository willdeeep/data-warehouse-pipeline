import pandas as pd

from loom_datagen.sessions import TRAFFIC_MEDIUMS


def test_sessions(frames):
    s = frames["sessions"]
    u = frames["users"]

    assert s["device_category"].isin(["desktop", "mobile", "tablet", "unknown"]).all()
    assert s["traffic_medium"].isin(TRAFFIC_MEDIUMS).all()

    known = s["user_crm_id"].dropna()
    assert set(known).issubset(set(u["user_crm_id"]))  # FK integrity for logged-in sessions
    assert known.shape[0] < s.shape[0]  # some anonymous sessions exist

    assert (pd.to_datetime(s["date"]) >= pd.Timestamp("2020-01-01")).all()

    # session_id / cookie ids must be high-cardinality (guards the hex-id generator)
    assert s["session_id"].nunique() > 0.99 * len(s)
    assert s["user_cookie_id"].nunique() > 0.99 * len(s)
