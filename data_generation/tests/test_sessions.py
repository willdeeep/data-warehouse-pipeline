import pandas as pd
from loom_datagen.domain.sessions import TRAFFIC_MEDIUMS


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


def test_logged_in_sessions_after_registration(frames):
    # Activity can't predate signup: every logged-in session must be dated on/after its user's
    # registration_date (transactions inherit session dates, so this bounds them too).
    s = frames["sessions"]
    u = frames["users"].drop_duplicates("user_crm_id")[["user_crm_id", "registration_date"]]
    known = s[s["user_crm_id"].notna()].merge(u, on="user_crm_id", how="left")
    assert (pd.to_datetime(known["date"]) >= pd.to_datetime(known["registration_date"])).all()
