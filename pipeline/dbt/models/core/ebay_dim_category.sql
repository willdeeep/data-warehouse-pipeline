{{ config(materialized='table') }}

select
  row_number() over(order by category) as category_id,
  category
from {{ source('ebay', 'ebay_transformed') }}
where category is not null
group by category
