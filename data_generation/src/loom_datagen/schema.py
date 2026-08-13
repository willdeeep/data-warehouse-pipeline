"""BigQuery schemas for the 10 loom_sync source tables.

Column names, data types, and descriptions mirror pipeline/dbt/models/sources/source.yml
exactly, so the loaded loom_sync tables are self-documenting in the BigQuery console and
INFORMATION_SCHEMA (#25). Modes are chosen so generated frames load without violating NOT NULL
where the generator guarantees a value, and stay NULLABLE where nulls are legitimate.

`_f`'s `desc` argument is required — a column cannot be added without a description.
"""

from __future__ import annotations

from google.cloud import bigquery as bq

_R = "REQUIRED"
_N = "NULLABLE"


def _f(name: str, dtype: str, desc: str, mode: str = _N) -> bq.SchemaField:
    return bq.SchemaField(name, dtype, mode=mode, description=desc)


_AD_CHANNELS = ["criteo", "google", "meta", "rtbhouse", "tiktok"]
# Display labels for the per-channel ad columns (mirrors source.yml wording).
_AD_CHANNEL_LABELS = {
    "criteo": "Criteo",
    "google": "Google Ads",
    "meta": "Meta (Facebook/Instagram)",
    "rtbhouse": "RTB House",
    "tiktok": "TikTok",
}


def _adplatform_columns() -> list[bq.SchemaField]:
    cols = [_f("date", "DATE", "Date of advertising activity", _R)]
    for ch in _AD_CHANNELS:
        label = _AD_CHANNEL_LABELS[ch]
        cols.append(
            _f(f"{ch}_clicks", "INTEGER", f"Number of clicks from {label} advertising campaigns")
        )
        cols.append(_f(f"{ch}_cost", "FLOAT", f"Total advertising spend on {label} in USD"))
        cols.append(
            _f(f"{ch}_impressions", "INTEGER", f"Number of ad impressions served through {label}")
        )
    return cols


SCHEMAS: dict[str, list[bq.SchemaField]] = {
    "adplatform_data": _adplatform_columns(),
    "funnelevents": [
        _f("date", "DATE", "Date when the event occurred", _R),
        _f("device_category", "STRING", "Type of device used (desktop, mobile, tablet)"),
        _f(
            "event_name",
            "STRING",
            "Name of the tracked event (page_view, add_to_cart, purchase, etc.)",
            _R,
        ),
        _f("event_time", "DATETIME", "Timestamp when the event occurred", _R),
        _f("item_id", "STRING", "Unique identifier for the product associated with the event"),
        _f("session_id", "STRING", "Unique identifier for the user session", _R),
        _f(
            "transaction_id",
            "STRING",
            "Unique identifier for the transaction (null for non-purchase events)",
        ),
        _f("user_cookie_id", "STRING", "Anonymous user identifier based on browser cookie"),
        _f("user_crm_id", "STRING", "Customer relationship management ID for registered users"),
    ],
    "product_costs": [
        _f("item_id", "STRING", "Unique identifier for the product", _R),
        _f("cost_of_item", "FLOAT", "Cost to acquire or manufacture the product in USD", _R),
    ],
    "product_listprices": [
        _f("item_id", "STRING", "Unique identifier for the product", _R),
        _f("item_list_price", "FLOAT", "Official list price of the product in USD", _R),
    ],
    "product_returns": [
        # One row per returned unit, referencing the specific item_id sold.
        _f("return_date", "DATE", "Date when the return was processed", _R),
        _f("transaction_id", "STRING", "Unique identifier for the original transaction", _R),
        _f(
            "item_id",
            "STRING",
            "Per-unit identifier of the specific returned item "
            "(FK to transactionsanditems.item_id)",
            _R,
        ),
        _f(
            "product_id",
            "STRING",
            "Product SKU of the returned item (FK to productattributes.item_id)",
            _R,
        ),
        _f(
            "return_quantity",
            "FLOAT",
            "Units returned in this row (always 1 — one row per returned unit)",
        ),
        _f("return_status", "STRING", "Status of the return (Refund, Exchange)"),
    ],
    "productattributes": [
        _f("item_id", "STRING", "Unique identifier for the product", _R),
        _f("item_brand", "STRING", "Brand name of the product"),
        _f("item_gender", "STRING", "Target gender for the product (male, female, unisex)"),
        _f("item_main_category", "STRING", "Primary category classification for the product"),
        _f("item_name", "STRING", "Display name of the product"),
        _f("item_sub_category", "STRING", "Secondary category classification for the product"),
    ],
    "sessions": [
        _f(
            "session_id",
            "STRING",
            "Session ID for the user session (each session will be recorded across multiple lines)",
            _R,
        ),
        _f("date", "DATE", "Date when the session occurred", _R),
        _f("city", "STRING", "City location of the user session"),
        _f("device_category", "STRING", "Type of device used (desktop, mobile, tablet)"),
        _f(
            "traffic_medium",
            "STRING",
            "Marketing medium that drove the session (organic, paid, email, etc.)",
        ),
        _f(
            "traffic_source",
            "STRING",
            "Specific source that drove the session (google, facebook, direct, etc.)",
        ),
        _f("user_cookie_id", "STRING", "Anonymous user identifier based on browser cookie"),
        _f("user_crm_id", "STRING", "Customer relationship management ID for registered users"),
    ],
    "transactions": [
        _f("transaction_id", "STRING", "Unique identifier for the transaction", _R),
        _f("date", "DATE", "Date when the transaction occurred", _R),
        _f(
            "session_id",
            "STRING",
            "Unique identifier for the session where transaction occurred",
            _R,
        ),
        _f("transaction_coupon", "STRING", "Coupon code applied to the transaction"),
        _f(
            "transaction_revenue",
            "FLOAT",
            "Total revenue from the transaction excluding shipping in USD",
        ),
        _f("transaction_shipping", "FLOAT", "Shipping cost charged for the transaction in USD"),
        _f(
            "transaction_total", "FLOAT", "Total amount charged including shipping and taxes in USD"
        ),
        _f("user_cookie_id", "STRING", "Anonymous user identifier based on browser cookie"),
        _f("user_crm_id", "STRING", "Customer relationship management ID for registered users"),
    ],
    "transactionsanditems": [
        # One row per unit sold: item_id is a globally-unique per-item key; product_id is the SKU.
        _f("item_id", "STRING", "Globally-unique per-unit line-item key (transaction grain)", _R),
        _f("transaction_id", "STRING", "Unique identifier for the transaction", _R),
        _f("product_id", "STRING", "Product SKU purchased (FK to productattributes.item_id)", _R),
        _f("date", "DATE", "Date when the transaction occurred", _R),
        _f("item_price", "FLOAT", "Price paid for the individual item in USD"),
        _f(
            "item_quantity", "INTEGER", "Number of units purchased for this item"
        ),  # always 1 (each row is one unit)
    ],
    "users": [
        _f("user_crm_id", "STRING", "Customer relationship management ID for registered users", _R),
        _f("city", "STRING", "City location of the user"),
        _f("first_purchase_date", "DATE", "Date of the users first purchase"),
        _f("latest_login_date", "DATE", "Most recent date the user logged into their account"),
        _f("latest_purchase_date", "DATE", "Most recent date the user made a purchase"),
        _f("opt_in_status", "BOOLEAN", "Whether the user has opted in to marketing communications"),
        _f("loom_plus_status", "BOOLEAN", "Is user enrolled in the Loom+ subscription program"),
        _f("loom_plus_tier", "STRING", "Loom+ subscription tier level"),
        _f("registration_date", "DATE", "Date when the user created their account"),
        _f("user_gender", "STRING", "Self-reported gender of the user"),
        _f(
            "valid_from",
            "DATE",
            "Effective date this profile version became current "
            "(SCD2 version key; half-open [valid_from, next valid_from)).",
            _R,
        ),
    ],
}
