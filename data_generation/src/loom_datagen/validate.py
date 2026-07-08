"""Post-load validation: query BigQuery to confirm integrity + accepted values."""
from __future__ import annotations

from google.cloud import bigquery

# (child_table, child_col) -> (parent_table, parent_col): child values must exist in parent.
_FOREIGN_KEYS = [
    ("transactions", "session_id", "sessions", "session_id"),
    ("transactionsanditems", "transaction_id", "transactions", "transaction_id"),
    ("transactionsanditems", "item_id", "productattributes", "item_id"),
    ("funnelevents", "session_id", "sessions", "session_id"),
    ("product_returns", "transaction_id", "transactions", "transaction_id"),
]

# table -> {column: allowed values}
_ACCEPTED_VALUES = {
    "users": {"user_gender": ["M", "F", "Non-binary", "Unknown"]},
    "sessions": {"device_category": ["desktop", "mobile", "tablet", "unknown"]},
    "product_returns": {"return_status": ["Refund", "Exchange"]},
}


def validate_bigquery(cfg) -> dict:
    """Return a report dict; keys: row_counts, orphans, violations. Raises on nothing."""
    client = bigquery.Client(project=cfg.project_id, location=cfg.bq_location)
    ds = f"`{cfg.project_id}.{cfg.source_dataset}`"

    report: dict = {"row_counts": {}, "orphans": 0, "violations": []}

    tables = [
        "productattributes", "product_costs", "product_listprices", "users", "sessions",
        "transactions", "transactionsanditems", "funnelevents", "product_returns",
        "adplatform_data",
    ]
    for t in tables:
        n = list(client.query(f"SELECT COUNT(*) c FROM {ds}.{t}").result())[0].c
        report["row_counts"][t] = n

    for child, ccol, parent, pcol in _FOREIGN_KEYS:
        sql = (
            f"SELECT COUNT(*) c FROM {ds}.{child} ch "
            f"LEFT JOIN {ds}.{parent} p ON ch.{ccol} = p.{pcol} "
            f"WHERE ch.{ccol} IS NOT NULL AND p.{pcol} IS NULL"
        )
        orphaned = list(client.query(sql).result())[0].c
        if orphaned:
            report["orphans"] += orphaned
            report["violations"].append(f"{child}.{ccol} -> {parent}.{pcol}: {orphaned} orphans")

    for table, cols in _ACCEPTED_VALUES.items():
        for col, allowed in cols.items():
            allowed_sql = ", ".join(f"'{v}'" for v in allowed)
            sql = (
                f"SELECT COUNT(*) c FROM {ds}.{table} "
                f"WHERE {col} IS NOT NULL AND {col} NOT IN ({allowed_sql})"
            )
            bad = list(client.query(sql).result())[0].c
            if bad:
                report["violations"].append(f"{table}.{col}: {bad} values outside accepted set")

    return report
