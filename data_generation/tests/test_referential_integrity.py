from loom_datagen.schema import SCHEMAS

EXPECTED = {
    "productattributes", "product_costs", "product_listprices", "users", "sessions",
    "transactions", "transactionsanditems", "funnelevents", "product_returns",
    "adplatform_data",
}


def test_all_ten_tables_present_and_nonempty(frames):
    assert set(frames) == EXPECTED
    assert all(len(df) > 0 for df in frames.values())


def test_column_sets_match_schema(frames):
    for name, df in frames.items():
        expected_cols = {f.name for f in SCHEMAS[name]}
        assert set(df.columns) == expected_cols, f"{name}: {set(df.columns) ^ expected_cols}"


def test_cross_table_foreign_keys(frames):
    users = set(frames["users"]["user_crm_id"])
    sessions = set(frames["sessions"]["session_id"])
    products = set(frames["productattributes"]["item_id"])
    txns = set(frames["transactions"]["transaction_id"])

    # sessions -> users (logged-in only)
    assert set(frames["sessions"]["user_crm_id"].dropna()).issubset(users)
    # transactions -> sessions
    assert set(frames["transactions"]["session_id"]).issubset(sessions)
    # line items -> transactions + products
    assert set(frames["transactionsanditems"]["transaction_id"]).issubset(txns)
    assert set(frames["transactionsanditems"]["item_id"]).issubset(products)
    # funnel events -> sessions
    assert set(frames["funnelevents"]["session_id"]).issubset(sessions)
    # returns -> transactions
    assert set(frames["product_returns"]["transaction_id"]).issubset(txns)


def test_reproducible_under_seed(cfg):
    from loom_datagen.build import build_all

    a = build_all(cfg)
    b = build_all(cfg)
    for name in EXPECTED:
        assert a[name].equals(b[name]), name
