"""Executable pandera data contracts for the 10 loom_sync generated frames.

Column names/types/nullability mirror ``infrastructure/schema.py`` (BigQuery load schema);
accepted-value sets mirror ``validation/validate.py``. Gate generated frames with
``validate_frames`` before they reach the loader.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

_GENDER_VALUES = ["M", "F", "Non-binary", "Unknown"]
_DEVICE_CATEGORY_VALUES = ["desktop", "mobile", "tablet", "unknown"]
_RETURN_STATUS_VALUES = ["Refund", "Exchange"]

_AD_CHANNELS = ["criteo", "google", "meta", "rtbhouse", "tiktok"]


def _adplatform_columns() -> dict[str, pa.Column]:
    cols: dict[str, pa.Column] = {"date": pa.Column("datetime64[ns]", nullable=False)}
    for ch in _AD_CHANNELS:
        cols[f"{ch}_clicks"] = pa.Column(int, nullable=True)
        cols[f"{ch}_cost"] = pa.Column(float, nullable=True)
        cols[f"{ch}_impressions"] = pa.Column(int, nullable=True)
    return cols


CONTRACTS: dict[str, pa.DataFrameSchema] = {
    "adplatform_data": pa.DataFrameSchema(_adplatform_columns(), strict=True, coerce=True),
    "funnelevents": pa.DataFrameSchema(
        {
            "date": pa.Column("datetime64[ns]", nullable=False),
            "device_category": pa.Column(str, nullable=True),
            "event_name": pa.Column(str, nullable=False),
            "event_time": pa.Column("datetime64[ns]", nullable=False),
            "item_id": pa.Column(str, nullable=True),
            "session_id": pa.Column(str, nullable=False),
            "transaction_id": pa.Column(str, nullable=True),
            "user_cookie_id": pa.Column(str, nullable=True),
            "user_crm_id": pa.Column(str, nullable=True),
        },
        strict=True,
        coerce=True,
    ),
    "product_costs": pa.DataFrameSchema(
        {
            "item_id": pa.Column(str, nullable=False),
            "cost_of_item": pa.Column(float, nullable=False),
        },
        strict=True,
        coerce=True,
    ),
    "product_listprices": pa.DataFrameSchema(
        {
            "item_id": pa.Column(str, nullable=False),
            "item_list_price": pa.Column(float, nullable=False),
        },
        strict=True,
        coerce=True,
    ),
    "product_returns": pa.DataFrameSchema(
        {
            "return_date": pa.Column("datetime64[ns]", nullable=False),
            "transaction_id": pa.Column(str, nullable=False),
            "item_id": pa.Column(str, nullable=False),
            "product_id": pa.Column(str, nullable=False),
            "return_quantity": pa.Column(float, nullable=True),
            "return_status": pa.Column(
                str, nullable=True, checks=pa.Check.isin(_RETURN_STATUS_VALUES)
            ),
        },
        strict=True,
        coerce=True,
    ),
    "productattributes": pa.DataFrameSchema(
        {
            "item_id": pa.Column(str, nullable=False),
            "item_brand": pa.Column(str, nullable=True),
            "item_gender": pa.Column(str, nullable=True),
            "item_main_category": pa.Column(str, nullable=True),
            "item_name": pa.Column(str, nullable=True),
            "item_sub_category": pa.Column(str, nullable=True),
        },
        strict=True,
        coerce=True,
    ),
    "sessions": pa.DataFrameSchema(
        {
            "session_id": pa.Column(str, nullable=False),
            "date": pa.Column("datetime64[ns]", nullable=False),
            "city": pa.Column(str, nullable=True),
            "device_category": pa.Column(
                str, nullable=True, checks=pa.Check.isin(_DEVICE_CATEGORY_VALUES)
            ),
            "traffic_medium": pa.Column(str, nullable=True),
            "traffic_source": pa.Column(str, nullable=True),
            "user_cookie_id": pa.Column(str, nullable=True),
            "user_crm_id": pa.Column(str, nullable=True),
        },
        strict=True,
        coerce=True,
    ),
    "transactions": pa.DataFrameSchema(
        {
            "transaction_id": pa.Column(str, nullable=False),
            "date": pa.Column("datetime64[ns]", nullable=False),
            "session_id": pa.Column(str, nullable=False),
            "transaction_coupon": pa.Column(str, nullable=True),
            "transaction_revenue": pa.Column(float, nullable=True),
            "transaction_shipping": pa.Column(float, nullable=True),
            "transaction_total": pa.Column(float, nullable=True),
            "user_cookie_id": pa.Column(str, nullable=True),
            "user_crm_id": pa.Column(str, nullable=True),
        },
        strict=True,
        coerce=True,
    ),
    "transactionsanditems": pa.DataFrameSchema(
        {
            "item_id": pa.Column(str, nullable=False),
            "transaction_id": pa.Column(str, nullable=False),
            "product_id": pa.Column(str, nullable=False),
            "date": pa.Column("datetime64[ns]", nullable=False),
            "item_price": pa.Column(float, nullable=True),
            "item_quantity": pa.Column(int, nullable=True),
        },
        strict=True,
        coerce=True,
    ),
    "users": pa.DataFrameSchema(
        {
            "user_crm_id": pa.Column(str, nullable=False),
            "city": pa.Column(str, nullable=True),
            "first_purchase_date": pa.Column("datetime64[ns]", nullable=True),
            "latest_login_date": pa.Column("datetime64[ns]", nullable=True),
            "latest_purchase_date": pa.Column("datetime64[ns]", nullable=True),
            "opt_in_status": pa.Column(bool, nullable=True),
            "loom_plus_status": pa.Column(bool, nullable=True),
            "loom_plus_tier": pa.Column(str, nullable=True),
            "registration_date": pa.Column("datetime64[ns]", nullable=True),
            "user_gender": pa.Column(str, nullable=True, checks=pa.Check.isin(_GENDER_VALUES)),
            "valid_from": pa.Column("datetime64[ns]", nullable=False),
        },
        strict=True,
        coerce=True,
    ),
}


def validate_frames(frames: dict[str, pd.DataFrame]) -> None:
    """Validate each generated frame against its contract, collecting all violations (lazy)."""
    for table, df in frames.items():
        schema = CONTRACTS.get(table)
        if schema is not None:
            schema.validate(df, lazy=True)  # raises pa.errors.SchemaErrors with ALL failures
