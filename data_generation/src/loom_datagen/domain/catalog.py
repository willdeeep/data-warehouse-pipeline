"""Product catalog generators: productattributes, product_costs, product_listprices."""

from __future__ import annotations

import numpy as np
import pandas as pd

FASHION_BRANDS = [
    "Adidas",
    "Nike",
    "Zara",
    "H&M",
    "Uniqlo",
    "Levi's",
    "Gap",
    "Puma",
    "Reebok",
    "ASOS",
]

CATEGORIES = {
    "shoes": ["sneakers", "boots", "sandals"],
    "tops": ["t-shirts", "shirts", "hoodies"],
    "bottoms": ["jeans", "shorts", "trousers"],
    "accessories": ["bags", "hats", "belts"],
}


def build_catalog(cfg, rng: np.random.Generator, fake):
    """Return (attrs, costs, prices) with a 1:1 item_id relationship and price >= cost."""
    n = cfg.n_products
    # Numeric SKU-style ids: the warehouse normalizes item_id -> INTEGER product keys,
    # so ids must be integer-castable strings (still STRING-typed per source.yml).
    ids = [str(100000 + i) for i in range(n)]

    main_cats = rng.choice(list(CATEGORIES), n)
    subs = [rng.choice(CATEGORIES[c]) for c in main_cats]
    brands = rng.choice(FASHION_BRANDS, n)

    attrs = pd.DataFrame(
        {
            "item_id": ids,
            "item_brand": brands,
            "item_gender": rng.choice(
                ["men", "women", "unisex", "kids"], n, p=[0.35, 0.35, 0.20, 0.10]
            ),
            "item_main_category": main_cats,
            "item_name": [f"{b} {s[:-1]}" for b, s in zip(brands, subs, strict=True)],
            "item_sub_category": subs,
        }
    )

    cost = rng.uniform(5, 120, n).round(2)
    costs = pd.DataFrame({"item_id": ids, "cost_of_item": cost})

    markup = rng.uniform(1.3, 3.0, n)
    prices = pd.DataFrame({"item_id": ids, "item_list_price": (cost * markup).round(2)})

    return attrs, costs, prices
