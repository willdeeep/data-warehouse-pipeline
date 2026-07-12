def test_catalog_referential_and_ranges(frames):
    attrs = frames["productattributes"]
    costs = frames["product_costs"]
    prices = frames["product_listprices"]

    assert attrs["item_id"].is_unique
    assert set(costs["item_id"]) == set(attrs["item_id"])  # 1:1 cost coverage
    assert set(prices["item_id"]) == set(attrs["item_id"])  # 1:1 price coverage
    assert (costs["cost_of_item"] >= 0).all()

    # list price >= cost for every item
    cost_by_item = costs.set_index("item_id")["cost_of_item"]
    price_vs_cost = prices.set_index("item_id")["item_list_price"] - cost_by_item
    assert (price_vs_cost >= 0).all()

    assert attrs["item_gender"].isin(["men", "women", "unisex", "kids"]).all()
