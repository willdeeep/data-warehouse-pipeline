import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Path to your raw extract CSV
base_dir = Path(__file__).resolve().parent.parent / "data"
input_csv = base_dir / "raw_extract.csv"
output_csv = base_dir / "ebay_brand_category_extract.csv"

print("Current working directory:", os.getcwd())
print("Looking for:", input_csv)

# Check if GOOGLE_APPLICATION_CREDENTIALS is set
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    print("❌ ERROR: The environment variable GOOGLE_APPLICATION_CREDENTIALS is not set.")
    print("Please set it to the path of your Google Cloud service account key file.")
    sys.exit(1)

# Set up BigQuery client (make sure GOOGLE_APPLICATION_CREDENTIALS is set)
client = bigquery.Client()

# Example: Fetch a table of brands and categories
query = """
    WITH brands AS (
        SELECT
            pa.item_brand AS brand,
            pa.item_sub_category AS sub_category,
            SUM(ti.item_quantity) AS total_items_sold
        FROM `loom-insights.dev_warehouse.stg_transactions_and_items` ti
        JOIN `loom-insights.dev_warehouse.stg_product_attributes` pa
            ON CAST(ti.item_id AS STRING) = pa.item_id
        WHERE pa.item_brand != 'Loom'
            AND pa.item_sub_category != 'Home & Decoration'
            AND pa.item_sub_category != 'Cosmetics & Makeup'
            AND pa.item_sub_category != 'Jewellery'
        GROUP BY pa.item_brand, pa.item_sub_category
        ORDER BY total_items_sold DESC
        LIMIT 100
    )
    SELECT brand, sub_category
    FROM brands
    ORDER BY total_items_sold DESC
    """
bq_df = client.query(query).to_dataframe()
bq_df = bq_df.rename(columns={'sub_category': 'category'})


def extract_brand_category(search_term, categories):
    known_brands = [
        "adidas", "reebok", "nike", "puma", "asics", "new balance", "converse", "vans", "under armour",
        "levis", "jack & jones", "national geographic", "u.s. polo assn.", "pierre cardin", "hummel",
        "calvin klein", "swarovski"
    ]
    leading_words = [
        "new", "latest", "original", "authentic", "genuine",
        "mens", "women", "womens", "kids", "unisex", "ladies", "boys", "girls", "child", "children", "male", "female"
    ]

    st = search_term.lower().strip()
    # Remove leading words
    for word in leading_words:
        if st.startswith(word + " "):
            st = st[len(word):].strip()
    # Find category from BigQuery categories (longest match first)
    found_cat = ""
    cat_idx = -1
    for cat in sorted(categories, key=lambda x: -len(x)):
        idx = st.find(cat.lower())
        if idx != -1:
            found_cat = cat
            cat_idx = idx
            break
    # Brand is everything before the category
    if found_cat:
        brand_part = st[:cat_idx].strip()
        # Remove leading words again
        for word in leading_words:
            if brand_part.startswith(word + " "):
                brand_part = brand_part[len(word):].strip()
        # Try to match brand from known brands
        brand = ""
        for b in sorted(known_brands, key=lambda x: -len(x)):
            if b in brand_part:
                brand = b.title()
                break
        if not brand:
            brand = ' '.join([w.capitalize() for w in brand_part.split()]) if brand_part else "Unknown"
        category = found_cat.title()
        return brand, category
    else:
        # Fallback: try to match brand only
        brand = ""
        for b in sorted(known_brands, key=lambda x: -len(x)):
            if st.startswith(b):
                brand = b.title()
                break
        if not brand:
            brand = st.split()[0].title() if st else "Unknown"
        category = st.split()[-1].title() if st else "Unknown"
        return brand, category


def extract_gender(search_term):
    gender_priority = ["womens", "mens", "unisex", "kids"]
    gender_keywords = {
        "womens": ["women", "womens", "woman's", "female", "ladies"],
        "mens": ["men", "mens", "man's", "male"],
        "unisex": ["unisex"],
        "kids": ["kids", "child", "children", "boys", "girls", "boy", "girl", "youth", "junior"]
    }
    st = search_term.lower()
    found = []
    for gender in gender_priority:
        for kw in gender_keywords[gender]:
            if kw in st:
                found.append(gender)
                break
    if found:
        # Return the highest priority gender found
        return found[0]
    return "unknown"


def main():
    df = pd.read_csv(input_csv)

    categories = bq_df['category'].dropna().unique().tolist()

    # Always extract brand, category, and gender from search_term

    def safe_extract(row):
        st = str(row["search_term"]) if pd.notnull(row["search_term"]) else ""
        title = str(row["title"]) if pd.notnull(row["title"]) else ""
        if not st.strip():
            return pd.Series({"brand": "Unknown", "category": "Unknown", "gender": "unknown"})
        brand, category = extract_brand_category(st, categories)
        gender = extract_gender(st)
        # Additional check for unisex: look for kids in title
        if gender == "unisex":
            kids_keywords = ["kids", "child", "children", "boys",
                             "girls", "boy", "girl", "youth", "junior"]
            title_lower = title.lower()
            if any(kw in title_lower for kw in kids_keywords):
                gender = "kids"
        if not brand:
            brand = "Unknown"
        if not category:
            category = "Unknown"
        if not gender:
            gender = "unknown"
        return pd.Series({"brand": brand, "category": category, "gender": gender})

    df[["brand", "category", "gender"]] = df.apply(safe_extract, axis=1)

    # Filter based on desired conditions
    desired_conditions = ['New with box', 'New with tags', 'New without tags']
    if "condition" in df.columns:
        df = df[df['condition'].isin(desired_conditions)]

    # Merge on both brand and category (case-insensitive)
    df['brand_lower'] = df['brand'].str.lower()
    df['category_lower'] = df['category'].str.lower()
    bq_df['brand_lower'] = bq_df['brand'].str.lower()
    bq_df['category_lower'] = bq_df['category'].str.lower()

    # Merge on both brand and category (case-insensitive)
    df = df.merge(
        bq_df[['brand_lower', 'category_lower', 'category']],
        on=['brand_lower', 'category_lower'],
        how='left',
        suffixes=('', '_bq')
    )

    # Prefer BigQuery category if available
    df['category'] = df['category_bq'].combine_first(df['category'])
    df = df.drop(columns=['brand_lower', 'category_lower', 'category_bq'])

    # Add transformation_timestamp column
    df['transformation_timestamp'] = datetime.now().date()

    # Get the list of columns
    cols = list(df.columns)

    # Find the positions
    condition_idx = cols.index('condition')
    gender_idx = cols.index('gender')

    # Remove 'gender' from its current position
    cols.pop(gender_idx)

    # Insert 'gender' after 'condition'
    cols.insert(condition_idx + 1, 'gender')

    # Reorder the DataFrame
    df = df[cols]

    df.to_csv(output_csv, index=False)
    print(f"✅ Saved cleaned data with brand, category, and gender to {output_csv}")

    table_id = os.getenv("BIGQUERY_TARGET_TABLE")
    upload_csv_to_bigquery(output_csv, table_id)


def upload_csv_to_bigquery(csv_path, table_id):
    """
    Uploads a CSV file to a BigQuery table.
    Args:
        csv_path (str): Path to the CSV file.
        table_id (str): Full BigQuery table ID in the format 'project.dataset.table'.
    """
    BIGQUERY_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if BIGQUERY_CREDENTIALS:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = BIGQUERY_CREDENTIALS
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Overwrite table
    )
    try:
        with open(str(csv_path), "rb") as source_file:
            job = client.load_table_from_file(source_file, table_id, job_config=job_config)
        job.result()
        logger.info(f"Uploaded {csv_path} to BigQuery table {table_id}")
    except Exception as e:
        logger.error(f"Failed to upload {csv_path} to BigQuery: {e}")


if __name__ == "__main__":
    main()
    # --- Add this block below ---
    table_id = os.getenv("BIGQUERY_TARGET_TABLE")  # Make sure this is set in your .env
    if table_id:
        upload_csv_to_bigquery(output_csv, table_id)
        print(f"✅ Uploaded cleaned data to BigQuery table: {table_id}")
    else:
        print("⚠️  BIGQUERY_TARGET_TABLE not set in .env, skipping upload.")
