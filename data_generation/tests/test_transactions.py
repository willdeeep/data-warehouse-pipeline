def test_transactions_and_items(frames):
    t = frames["transactions"]
    ti = frames["transactionsanditems"]
    s = frames["sessions"]

    assert t["transaction_id"].is_unique
    assert set(t["session_id"]).issubset(set(s["session_id"]))
    # one row per unit sold: item_id is the globally-unique grain key, quantity is always 1
    assert ti["item_id"].is_unique
    assert (ti["item_quantity"] == 1).all()
    assert (ti["item_price"] >= 0).all()

    # revenue equals sum of unit prices; total = revenue + shipping
    line_rev = ti["item_price"].groupby(ti["transaction_id"]).sum()
    merged = t.set_index("transaction_id")
    assert ((merged["transaction_revenue"] - line_rev).abs() < 0.01).all()
    total_check = merged["transaction_total"] - (
        merged["transaction_revenue"] + merged["transaction_shipping"]
    )
    assert (total_check.abs() < 0.01).all()

    # every unit references a real transaction and a real product
    assert set(ti["transaction_id"]).issubset(set(t["transaction_id"]))
    assert set(ti["product_id"]).issubset(set(frames["productattributes"]["item_id"]))


def test_each_unit_is_its_own_row(frames):
    # A product bought with quantity > 1 must appear as multiple rows sharing (transaction, product)
    # but with distinct item_ids — so individual units can be returned separately.
    ti = frames["transactionsanditems"]
    per_pair = ti.groupby(["transaction_id", "product_id"]).size()
    assert (per_pair >= 1).all()
    assert per_pair.max() > 1, "expected at least one multi-unit (transaction, product) line"
    # within any such pair, item_ids are distinct
    dup_pairs = per_pair[per_pair > 1].index
    for txn, prod in dup_pairs[:20]:
        rows = ti[(ti["transaction_id"] == txn) & (ti["product_id"] == prod)]
        assert rows["item_id"].is_unique
