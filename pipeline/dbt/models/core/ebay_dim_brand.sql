{{ config(materialized='table') }}

select
  row_number() over(order by brand) as brand_id,
  brand
from {{ source('ebay', 'ebay_transformed') }}
where brand is not null
group by brand