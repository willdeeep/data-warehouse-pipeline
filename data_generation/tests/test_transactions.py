def test_transactions_and_items(frames):
    t = frames["transactions"]
    ti = frames["transactionsanditems"]
    s = frames["sessions"]

    assert t["transaction_id"].is_unique
    assert set(t["session_id"]).issubset(set(s["session_id"]))
    assert (ti["item_quantity"] >= 1).all()
    assert (ti["item_price"] >= 0).all()

    # revenue equals sum of line items; total = revenue + shipping
    line_rev = (ti["item_price"] * ti["item_quantity"]).groupby(ti["transaction_id"]).sum()
    merged = t.set_index("transaction_id")
    assert ((merged["transaction_revenue"] - line_rev).abs() < 0.01).all()
    total_check = merged["transaction_total"] - (
        merged["transaction_revenue"] + merged["transaction_shipping"]
    )
    assert (total_check.abs() < 0.01).all()

    # every line item references a real transaction and a real product
    assert set(ti["transaction_id"]).issubset(set(t["transaction_id"]))
    assert set(ti["item_id"]).issubset(set(frames["productattributes"]["item_id"]))
