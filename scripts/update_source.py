"""Update source.yml based on table schema defined in table_schema.csv."""
import pandas as pd
import yaml

def load_csv(csv_path):
    """Load the CSV file into a DataFrame."""
    return pd.read_csv(csv_path)

def load_source_yml(source_yml_path):
    """Load the source.yml file."""
    with open(source_yml_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def format_column(column_name, description="", data_type=None, tests=None):
    """Format a column dictionary to match the patterns in source.yml."""
    column = {"name": column_name, "description": description}
    if data_type:
        column["data_type"] = data_type
    if tests:
        column["tests"] = tests
    return column

def update_source_yml(schema_df, source_data):
    """Update the source.yml data based on the schema DataFrame."""
    source_tables = {table["name"]: table for table in source_data["sources"][0]["tables"]}

    for _, row in schema_df.iterrows():
        table_name = row["table_name"]
        column_name = row["column_name"]
        data_type = row["data_type"]

        # Check if table exists in source.yml
        if table_name not in source_tables:
            source_tables[table_name] = {
                "name": table_name,
                "description": "",
                "columns": []
            }

        # Check if column exists in the table
        table = source_tables[table_name]
        column = next((col for col in table.get("columns", []) if col["name"] == column_name), None)

        if column:
            # Update data type if missing
            if "data_type" not in column:
                column["data_type"] = data_type
        else:
            # Add missing column without tests
            table.setdefault("columns", []).append(
                format_column(column_name, description="", data_type=data_type)
            )

    # Sort tables and columns for consistent formatting
    source_data["sources"][0]["tables"] = sorted(
        source_tables.values(), key=lambda x: x["name"]
    )
    for table in source_data["sources"][0]["tables"]:
        table["columns"] = sorted(table["columns"], key=lambda x: x["name"])

    return source_data

def save_source_yml(source_data, source_yml_path):
    """Save the updated source.yml data back to the file."""
    with open(source_yml_path, "w", encoding="utf-8") as file:
        file.write("version: 2\n\n")  # Write the header
        yaml.dump(
            {
                "sources": [
                    {
                        "name": "loom_sync",
                        "database": "loom-acquire",
                        "schema": "loom_sync",
                        "tables": source_data["sources"][0]["tables"],
                    }
                ]
            },
            file,
            default_flow_style=False,
            sort_keys=False,
            width=100,  # Ensure proper line wrapping for readability
            indent=2,  # Correct indentation for nested attributes
        )

    # Insert a newline between each column definition for readability
    with open(source_yml_path, "r", encoding="utf-8") as file:
        content = file.read()

    content = content.replace("\n  - name:", "\n\n  - name:")

    with open(source_yml_path, "w", encoding="utf-8") as file:
        file.write(content)

def main():
    """
    Main function to update the source.yml file based on the table schema
    defined in table_schema.csv.

    This script:
    1. Loads the table schema from a CSV file.
    2. Validates and updates the source.yml file by:
    - Adding missing tables and columns with empty descriptions.
    - Updating data type tests for columns without them.
    - Ensuring existing descriptions and tests remain unchanged.
    3. Saves the updated source.yml file.

    Usage:
    Run the script directly to update the source.yml file.
    """
    csv_path = "table_schema.csv"
    source_yml_path = "pipeline/dbt/models/source.yml"

    schema_df = load_csv(csv_path)
    source_data = load_source_yml(source_yml_path)

    updated_source_data = update_source_yml(schema_df, source_data)
    save_source_yml(updated_source_data, source_yml_path)

    print(f"{source_yml_path} updated successfully.")

if __name__ == "__main__":
    main()
