EVENTS = ["page_view", "view_item", "add_to_cart", "begin_checkout", "purchase", "remove_from_cart"]


def test_events_and_returns(frames):
    fe = frames["funnelevents"]
    ret = frames["product_returns"]
    t = frames["transactions"]
    ti = frames["transactionsanditems"]

    assert fe["event_name"].isin(EVENTS).all()

    # purchase events carry a real transaction_id; non-purchase events do not
    purchases = fe.loc[fe.event_name == "purchase", "transaction_id"]
    assert purchases.notna().all()
    assert set(purchases).issubset(set(t["transaction_id"]))
    assert fe.loc[fe.event_name != "purchase", "transaction_id"].isna().all()

    # every event references a real session
    assert set(fe["session_id"]).issubset(set(frames["sessions"]["session_id"]))

    # returns: valid status, each references a real sold item_id, one unit per return
    assert ret["return_status"].isin(["Refund", "Exchange"]).all()
    assert set(ret["item_id"]).issubset(set(ti["item_id"]))
    assert set(map(tuple, ret[["transaction_id", "item_id"]].to_numpy())).issubset(
        set(map(tuple, ti[["transaction_id", "item_id"]].to_numpy()))
    )
    assert (ret["return_quantity"] == 1).all()
