/*
===================================================================================
MODEL: dim_products
=========================    SELECT 
        s.*,
        {{ dbt_utils.generate_surrogate_key(['s.product_id', 's.dbt_valid_from']) }} AS product_surrogate_key,=======================================================

PURPOSE:
    Product dimension table combining product attributes, pricing, and cost data.
    Implements Slowly Changing Dimension Type 2 logic for tracking product changes over time.

SOURCES:
    - {{ ref('stg_product_attributes') }}
    - {{ ref('stg_product_list_prices') }}
    - {{ ref('stg_product_costs') }}

GRAIN:
    One row per unique product per time period (item_id + valid_from)

KEY ATTRIBUTES:
    - Product hierarchy (brand, categories)
    - Pricing and cost information
    - Product specifications and targeting
    - SCD Type 2 tracking fields

SCD LOGIC:
    - Tracks changes in product attributes, pricing, and costs over time
    - Creates new records when changes are detected in any source
    - Maintains historical versions with valid_from/valid_to dates
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['product_surrogate_key'], 'type': 'btree'},
        {'columns': ['product_id'], 'type': 'btree'},
        {'columns': ['brand'], 'type': 'btree'},
        {'columns': ['is_current'], 'type': 'btree'},
        {'columns': ['valid_from', 'valid_to'], 'type': 'btree'}
    ]
) }}

WITH product_base AS (
    SELECT
        -- Product identifiers (using natural key as primary key, cast to INTEGER)
        SAFE_CAST(item_id AS INTEGER) AS product_id,
        item_brand AS brand,
        item_name AS name,
        item_main_category AS main_category,
        item_sub_category AS sub_category,
        item_gender AS gender_target,
        
        -- dbt metadata from attributes
        dbt_updated_at AS attributes_updated_at,
        dbt_valid_from AS attributes_valid_from
        
    FROM {{ ref('stg_product_attributes') }}
    WHERE item_id IS NOT NULL
),

product_pricing AS (
    SELECT
        product_id,
        list_price,
        dbt_updated_at AS pricing_updated_at,
        dbt_valid_from AS pricing_valid_from
    FROM {{ ref('stg_product_list_prices') }}
    WHERE product_id IS NOT NULL
),

product_costs AS (
    SELECT
        product_id,
        product_cost AS unit_cost,
        dbt_updated_at AS cost_updated_at,
        dbt_valid_from AS cost_valid_from
    FROM {{ ref('stg_product_costs') }}
    WHERE product_id IS NOT NULL
),

products_combined AS (
    SELECT
        pb.product_id,
        pb.brand,
        pb.name,
        pb.main_category,
        pb.sub_category,
        pb.gender_target,
        
        -- Pricing information
        COALESCE(pp.list_price, 0.0) AS list_price,
        COALESCE(pc.unit_cost, 0.0) AS unit_cost,
        
        -- Calculated profit margin
        CASE 
            WHEN COALESCE(pp.list_price, 0) > 0 
            THEN SAFE_DIVIDE(
                (COALESCE(pp.list_price, 0) - COALESCE(pc.unit_cost, 0)), 
                COALESCE(pp.list_price, 0)
            )
            ELSE 0.0 
        END AS profit_margin,
        
        -- Combined metadata (use latest update across all sources)
        GREATEST(
            pb.attributes_updated_at,
            COALESCE(pp.pricing_updated_at, pb.attributes_updated_at),
            COALESCE(pc.cost_updated_at, pb.attributes_updated_at)
        ) AS dbt_updated_at,
        
        GREATEST(
            pb.attributes_valid_from,
            COALESCE(pp.pricing_valid_from, pb.attributes_valid_from),
            COALESCE(pc.cost_valid_from, pb.attributes_valid_from)
        ) AS dbt_valid_from,
        
        -- SCD Type 2 fields
        TRUE AS is_current  -- Source data is always current
        
    FROM product_base pb
    LEFT JOIN product_pricing pp ON pb.product_id = pp.product_id
    LEFT JOIN product_costs pc ON pb.product_id = pc.product_id
),

-- Simple table materialization - creates current snapshot of all products
final AS (
    SELECT 
        {{ dbt_utils.generate_surrogate_key(['product_id', 'dbt_valid_from']) }} AS product_surrogate_key,
        product_id,
        brand,
        name,
        main_category,
        sub_category,
        gender_target,
        list_price,
        unit_cost,
        profit_margin,
        
        -- SCD Type 2 fields
        CURRENT_TIMESTAMP() AS valid_from,
        CAST(NULL AS TIMESTAMP) AS valid_to,
        TRUE AS is_current,
        
        -- Metadata
        dbt_updated_at,
        CURRENT_TIMESTAMP() AS dbt_created_at
        
    FROM products_combined
)

SELECT * FROM final
