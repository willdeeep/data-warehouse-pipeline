"""Accept/reject tests for the pandera data contracts in validation/contracts.py.

Each contract is ``strict=True, coerce=True``. These tests exercise: a fully-valid frame
(accept), an accepted-values violation per ``isin``-constrained column (reject), an extra
unexpected column (reject, proves ``strict=True``), and a null in a required column (reject).
"""

from __future__ import annotations

import pandas as pd
import pandera
import pytest
from loom_datagen.validation.contracts import CONTRACTS


def _valid_users_row() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_crm_id": ["crm-0001"],
            "city": ["London"],
            "first_purchase_date": [pd.Timestamp("2024-01-15")],
            "latest_login_date": [pd.Timestamp("2024-03-01")],
            "latest_purchase_date": [pd.Timestamp("2024-02-20")],
            "opt_in_status": [True],
            "loom_plus_status": [False],
            "loom_plus_tier": ["Silver"],
            "registration_date": [pd.Timestamp("2024-01-01")],
            "user_gender": ["F"],
            "valid_from": [pd.Timestamp("2024-01-01")],
        }
    )


def _valid_sessions_row() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_id": ["sess-0001"],
            "date": [pd.Timestamp("2024-01-15")],
            "city": ["Paris"],
            "device_category": ["mobile"],
            "traffic_medium": ["cpc"],
            "traffic_source": ["google"],
            "user_cookie_id": ["cookie-0001"],
            "user_crm_id": ["crm-0001"],
        }
    )


def _valid_product_returns_row() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "return_date": [pd.Timestamp("2024-01-20")],
            "transaction_id": ["txn-0001"],
            "item_id": ["item-0001"],
            "product_id": ["prod-0001"],
            "return_quantity": [1.0],
            "return_status": ["Refund"],
        }
    )


def test_valid_users_frame_passes():
    """A fully-valid, single-row users frame (every column present) does not raise."""
    CONTRACTS["users"].validate(_valid_users_row())


def test_users_bad_gender_is_rejected():
    """An out-of-set user_gender value fails the isin check under lazy validation."""
    df = _valid_users_row()
    df["user_gender"] = ["Other"]
    with pytest.raises(pandera.errors.SchemaErrors):
        CONTRACTS["users"].validate(df, lazy=True)


def test_sessions_bad_device_category_is_rejected():
    """An out-of-set device_category value fails the isin check under lazy validation."""
    df = _valid_sessions_row()
    df["device_category"] = ["smart-fridge"]
    with pytest.raises(pandera.errors.SchemaErrors):
        CONTRACTS["sessions"].validate(df, lazy=True)


def test_product_returns_bad_return_status_is_rejected():
    """An out-of-set return_status value fails the isin check under lazy validation."""
    df = _valid_product_returns_row()
    df["return_status"] = ["Cancelled"]
    with pytest.raises(pandera.errors.SchemaErrors):
        CONTRACTS["product_returns"].validate(df, lazy=True)


def test_users_extra_column_is_rejected_by_strict():
    """An otherwise-valid users frame with an unexpected extra column fails strict=True."""
    df = _valid_users_row()
    df["unexpected_column"] = ["surprise"]
    with pytest.raises(pandera.errors.SchemaErrors):
        CONTRACTS["users"].validate(df, lazy=True)


def test_users_null_in_required_column_is_rejected():
    """A null in the non-nullable user_crm_id column fails the nullable=False constraint."""
    df = _valid_users_row()
    df["user_crm_id"] = [None]
    with pytest.raises(pandera.errors.SchemaErrors):
        CONTRACTS["users"].validate(df, lazy=True)
