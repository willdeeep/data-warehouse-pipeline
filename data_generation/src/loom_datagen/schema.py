"""BigQuery schemas for the 10 loom_sync source tables.

Column names and data types mirror pipeline/dbt/models/sources/source.yml exactly.
Modes are chosen so generated frames load without violating NOT NULL where the
generator guarantees a value, and stay NULLABLE where nulls are legitimate.
"""

from __future__ import annotations

from google.cloud import bigquery as bq

_R = "REQUIRED"
_N = "NULLABLE"


def _f(name: str, dtype: str, mode: str = _N) -> bq.SchemaField:
    return bq.SchemaField(name, dtype, mode=mode)


_AD_CHANNELS = ["criteo", "google", "meta", "rtbhouse", "tiktok"]


def _adplatform_columns() -> list[bq.SchemaField]:
    cols = [_f("date", "DATE", _R)]
    for ch in _AD_CHANNELS:
        cols.append(_f(f"{ch}_clicks", "INTEGER"))
        cols.append(_f(f"{ch}_cost", "FLOAT"))
        cols.append(_f(f"{ch}_impressions", "INTEGER"))
    return cols


SCHEMAS: dict[str, list[bq.SchemaField]] = {
    "adplatform_data": _adplatform_columns(),
    "funnelevents": [
        _f("date", "DATE", _R),
        _f("device_category", "STRING"),
        _f("event_name", "STRING", _R),
        _f("event_time", "DATETIME", _R),
        _f("item_id", "STRING"),
        _f("session_id", "STRING", _R),
        _f("transaction_id", "STRING"),
        _f("user_cookie_id", "STRING"),
        _f("user_crm_id", "STRING"),
    ],
    "product_costs": [
        _f("item_id", "STRING", _R),
        _f("cost_of_item", "FLOAT", _R),
    ],
    "product_listprices": [
        _f("item_id", "STRING", _R),
        _f("item_list_price", "FLOAT", _R),
    ],
    "product_returns": [
        _f("return_date", "DATE", _R),
        _f("transaction_id", "STRING", _R),
        _f("item_id", "STRING", _R),
        _f("item_quantity", "INTEGER"),
        _f("return_quantity", "FLOAT"),
        _f("return_status", "STRING"),
    ],
    "productattributes": [
        _f("item_id", "STRING", _R),
        _f("item_brand", "STRING"),
        _f("item_gender", "STRING"),
        _f("item_main_category", "STRING"),
        _f("item_name", "STRING"),
        _f("item_sub_category", "STRING"),
    ],
    "sessions": [
        _f("session_id", "STRING", _R),
        _f("date", "DATE", _R),
        _f("city", "STRING"),
        _f("device_category", "STRING"),
        _f("traffic_medium", "STRING"),
        _f("traffic_source", "STRING"),
        _f("user_cookie_id", "STRING"),
        _f("user_crm_id", "STRING"),
    ],
    "transactions": [
        _f("transaction_id", "STRING", _R),
        _f("date", "DATE", _R),
        _f("session_id", "STRING", _R),
        _f("transaction_coupon", "STRING"),
        _f("transaction_revenue", "FLOAT"),
        _f("transaction_shipping", "FLOAT"),
        _f("transaction_total", "FLOAT"),
        _f("user_cookie_id", "STRING"),
        _f("user_crm_id", "STRING"),
    ],
    "transactionsanditems": [
        _f("transaction_id", "STRING", _R),
        _f("item_id", "STRING", _R),
        _f("date", "DATE", _R),
        _f("item_price", "FLOAT"),
        _f("item_quantity", "INTEGER"),
    ],
    "users": [
        _f("user_crm_id", "STRING", _R),
        _f("city", "STRING"),
        _f("first_purchase_date", "DATE"),
        _f("latest_login_date", "DATE"),
        _f("latest_purchase_date", "DATE"),
        _f("opt_in_status", "BOOLEAN"),
        _f("loom_plus_status", "BOOLEAN"),
        _f("loom_plus_tier", "STRING"),
        _f("registration_date", "DATE"),
        _f("user_gender", "STRING"),
        _f("valid_from", "DATE", _R),
    ],
}
