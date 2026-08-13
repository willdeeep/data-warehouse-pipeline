"""Extracts raw data from eBay API using search terms from BigQuery and saves to a CSV file."""

import base64
import logging
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)  # will find your .env file

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Debug: Check if credentials are loaded (without exposing full values)
logging.info("CLIENT_ID loaded: %s", "Yes" if CLIENT_ID else "No")
logging.info("CLIENT_SECRET loaded: %s", "Yes" if CLIENT_SECRET else "No")
if CLIENT_ID:
    logging.info("CLIENT_ID length: %d characters", len(CLIENT_ID))
if CLIENT_SECRET:
    logging.info("CLIENT_SECRET length: %d characters", len(CLIENT_SECRET))

BIGQUERY_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = BIGQUERY_CREDENTIALS
export_csv = os.getenv("RAW_CSV_PATH")

# Log the paths being used
logging.info("Using RAW_CSV_PATH: %s", export_csv)

# Ensure paths are not None
if not export_csv:
    raise ValueError("Environment variable RAW_CSV_PATH is not set.")

# Initialize BigQuery client
client = bigquery.Client()


def fetch_search_terms():
    """
    Fetches brand and sub-category combinations from BigQuery to use as search terms.
    Gets the top 10 brand+category combinations, then creates 3 search terms for each:
    - "new {brand} {category} mens"
    - "new {brand} {category} womens"
    - "new {brand} {category} unisex"

    This results in 30 total search terms (10 combinations × 3 genders).
    Excludes Loom brand and certain categories, ordered by frequency.

    Returns:
        list: A list of search terms combining brand, sub-category, and gender.
    """

    # Query for top 10 brand-subcategory combinations (regardless of gender)
    query = """
    WITH brands AS (
        SELECT
            pa.item_brand AS brand,
            pa.item_sub_category AS sub_category,
            SUM(ti.product_quantity) AS total_items_sold
        FROM `loom-insights.dev_warehouse.stg_transactions_and_items` ti
        JOIN `loom-insights.dev_warehouse.stg_product_attributes` pa
            ON CAST(ti.product_id AS STRING) = pa.item_id
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

    query_job = client.query(query)
    all_search_terms = []

    # For each brand+category combination, create 3 gender variants
    combinations_count = 0
    for row in query_job:
        # Create search terms for each gender
        mens_term = f"new {row.brand} {row.sub_category} mens".lower()
        womens_term = f"new {row.brand} {row.sub_category} womens".lower()
        unisex_term = f"new {row.brand} {row.sub_category} unisex".lower()

        all_search_terms.extend([mens_term, womens_term, unisex_term])
        combinations_count += 1

    print(f"Generated search terms from {combinations_count} brand category combinations: ")
    print(f"  - Mens terms: {combinations_count}")
    print(f"  - Womens terms: {combinations_count}")
    print(f"  - Unisex terms: {combinations_count}")
    print(f"Total search terms: {len(all_search_terms)}")

    return all_search_terms


def get_access_token(client_id, client_secret):
    """
    Retrieve an OAuth access token from the eBay API.

    Args:
        client_id (str): eBay application client ID.
        client_secret (str): eBay application client secret.

    Returns:
        str: eBay access token.
    """

    auth_string = f"{client_id}:{client_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"}

    response = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token", headers=headers, data=data, timeout=10
    )
    response.raise_for_status()
    return response.json()["access_token"]


def search_ebay_items(query, token, limit, offset_param):
    """
    Search for items on eBay using the Browse API.

    Args:
        query (str): The search term to query eBay for.
        token (str): OAuth access token for eBay API authentication.
        limit (int): Maximum number of results to return in this request.
        offset_param (int): The starting index of the results to return (for pagination).

    Returns:
        list: A list of item summary dictionaries returned by the eBay API.
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=GB",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",  # <-- for GB marketplace
    }

    params = {
        "q": query,
        "limit": limit,
        "offset": offset_param,
        "category_ids": "11450",  # Clothing
        "buyerCountry": "GB",
        "filter": "priceCurrency:GBP",
        "item_location_country": "GB",
    }

    response = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers=headers,
        params=params,
        timeout=10,  # Set a timeout for the request
    )
    response.raise_for_status()
    return response.json().get("itemSummaries", [])


def save_to_csv(items, filename):
    """
    Save a list of eBay item dictionaries to a CSV file.

    Args:
        items (list): List of dictionaries, each representing an eBay item.
        filename (str): Path to the CSV file to write.
    """
    rows = []
    for item in items:
        rows.append(
            {
                "search_term": item.get("search_term"),
                "title": item.get("title", ""),
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency"),
                "category": item.get("categoryPath"),
                "brand": item.get("brand"),
                "condition": item.get("condition"),
                "url": item.get("itemWebUrl"),
            }
        )

    df = pd.DataFrame(rows)
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    # Ensure the directory exists before saving
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filename, index=True, index_label="id")
    print(f"✅ Saved {len(df)} products to {filename}")


def extract_raw_data():
    """
    Extract raw data from eBay API using top 100 brand+subcategory combinations,
    saving top 10 results for each search term to raw_extract.csv.
    """
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    print("🔐 Access token retrieved")

    search_terms = fetch_search_terms()
    print(f"📊 Found {len(search_terms)} brand+subcategory combinations to search")

    all_results = []

    for i, term in enumerate(search_terms, 1):
        print(f"🔎 [{i}/{len(search_terms)}] Searching for '{term}' (top 10 results)...")

        # Get top 20 results for this search term
        batch = search_ebay_items(term, access_token, limit=10, offset_param=0)

        if not batch:
            print(f"📭 No items found for '{term}'")
        else:
            # Add search term to each item and validate GBP price
            for item in batch:
                item["search_term"] = term
                if item.get("price", {}).get("currency") != "GBP":
                    logging.warning(
                        "Non-GBP price found: %s for item '%s' (search term: '%s')",
                        item.get("price"),
                        item.get("title", ""),
                        term,
                    )
            all_results.extend(batch)
            print(f"✅ Found {len(batch)} items for '{term}'")

        # Add a small delay to be respectful to eBay's API
        time.sleep(0.5)

    print(f"\n🎉 Total items collected: {len(all_results)}")
    save_to_csv(all_results, filename=export_csv)

    logging.info("Raw data saved to %s", export_csv)


def main():
    """Main function for data extraction pipeline."""
    extract_raw_data()


if __name__ == "__main__":
    extract_raw_data()
