def test_adspend(frames):
    a = frames["adplatform_data"]
    assert a["date"].is_unique
    for ch in ["criteo", "google", "meta", "rtbhouse", "tiktok"]:
        assert (a[f"{ch}_clicks"] >= 0).all()
        assert (a[f"{ch}_cost"] >= 0).all()
        assert (a[f"{ch}_impressions"] >= a[f"{ch}_clicks"]).all()  # clicks <= impressions
