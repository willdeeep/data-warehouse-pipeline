{{ config(materialized='table') }}

with
  brands as (select brand, brand_id from {{ ref('ebay_dim_brand') }}),
  categories as (select category, category_id from {{ ref('ebay_dim_category') }})
select
  t.id,
  t.search_term,
  t.title,
  t.price,
  t.currency,
  b.brand_id,
  c.category_id,
  t.condition,
  t.gender,
  t.url,
  t.transformation_timestamp
from {{ source('ebay', 'ebay_transformed') }} t
left join brands b on t.brand = b.brand
left join categories c on t.category = c.category
where b.brand_id is not null
  and c.category_id is not null
