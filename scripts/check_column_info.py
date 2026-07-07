"""Check and validate BigQuery table schemas against source.yml definitions.
This script loads environment variables, retrieves table schemas from BigQuery,
and compares them with the definitions in source.yml. It generates a CSV report
of the schema information.
"""
#  Standard Imports
import os
# Third-party Imports
from google.cloud import bigquery
import pandas as pd
from dotenv import load_dotenv
import yaml

def load_env_variables():
    """Load environment variables from .env file."""
    load_dotenv()
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set. Check your .env file.")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    return creds_path

def load_source_definitions(source_yml_path):
    """Load source.yml definitions."""
    with open(source_yml_path, "r", encoding="utf-8") as file:
        source_definitions = yaml.safe_load(file)
    return {table["name"]:
        {col["name"]: col for col in table.get("columns", [])}
        for table in source_definitions["sources"][0]["tables"]}

def build_dataframe(client, project, dataset, tables):
    """Build a DataFrame of table_name, column_name, and data_type for all columns in all tables."""
    schema_info = []
    for table_name in tables:
        table_id = f"{project}.{dataset}.{table_name}"
        table = client.get_table(table_id)
        schema_info.extend([
            {"table_name": table_name, "column_name": field.name,
             "data_type": field.field_type, "column_order": idx}
            for idx, field in enumerate(table.schema)
        ])
    return pd.DataFrame(schema_info).sort_values(
        by=["table_name", "column_order"]).drop(columns=["column_order"])

def validate_dataframe(df, source_tables):
    """Validate each row in the DataFrame against source.yml and add a test_result column."""
    test_results = []
    for _, row in df.iterrows():
        table_name = row["table_name"]
        column_name = row["column_name"]
        data_type = row["data_type"]

        if table_name not in source_tables:
            test_results.append("table_missing")
            continue

        if column_name not in source_tables[table_name]:
            test_results.append("column_missing")
            continue

        expected_data_type = source_tables[table_name][column_name].get("data_type")
        if not expected_data_type:
            test_results.append("no_dt")
        elif expected_data_type != data_type:
            test_results.append("wrong_dt")
        else:
            test_results.append("all_okay")

    df["test_result"] = test_results
    return df

def save_schema_to_csv(df, csv_path):
    """Save schema information to a CSV file."""
    df.to_csv(csv_path, index=False)
    print(f"Saved schema for all tables to {csv_path}")

def main():
    """main _summary_
    """
    creds_path = load_env_variables()
    print(f"Using credentials from: {creds_path}")

    source_yml_path = "pipeline/dbt/models/sources/source.yml"
    source_tables = load_source_definitions(source_yml_path)

    client = bigquery.Client()
    dataset = "loom_sync"
    project = "loom-insights"
    tables = [
        "adplatform_data",
        "sessions",
        "transactions",
        "transactionsanditems",
        "productattributes",
        "product_returns",
        "product_listprices",
        "product_costs",
        "funnelevents",
        "users"
    ]

    df = build_dataframe(client, project, dataset, tables)
    df = validate_dataframe(df, source_tables)
    csv_path = "table_schema.csv"
    save_schema_to_csv(df, csv_path)

if __name__ == "__main__":
    main()
