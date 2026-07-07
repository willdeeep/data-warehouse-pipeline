/*
===================================================================================
MODEL: dim_date
===================================================================================

PURPOSE:
    Date dimension table providing calendar attributes for fact table joins.
    Generates dates from 2020 to 2030 with comprehensive date attributes.

GRAIN:
    One row per calendar date

KEY ATTRIBUTES:
    - Date hierarchies (day, week, month, quarter, year)
    - Business logic flags (weekend, holiday indicators)
    - Date key for efficient joins

DATA SOURCES:
    - Generated using dbt date spine utility
*/

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['date_key'], 'type': 'btree'},
        {'columns': ['date'], 'type': 'btree'}
    ]
) }}

WITH date_spine AS (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2030-12-31' as date)"
    ) }}
),

date_dimension AS (
    SELECT
        -- Primary key: YYYYMMDD format
        CAST(FORMAT_DATE('%Y%m%d', date_day) AS INT64) AS date_key,
        
        -- Date attributes
        date_day AS date,
        EXTRACT(DAYOFWEEK FROM date_day) AS day_of_week,
        EXTRACT(MONTH FROM date_day) AS month,
        EXTRACT(QUARTER FROM date_day) AS quarter,
        EXTRACT(YEAR FROM date_day) AS year,
        
        -- Business logic flags
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM date_day) IN (1, 7) THEN TRUE 
            ELSE FALSE 
        END AS is_weekend,
        
        -- Simple holiday logic (can be enhanced with actual holiday calendar)
        CASE 
            WHEN EXTRACT(MONTH FROM date_day) = 12 AND EXTRACT(DAY FROM date_day) = 25 THEN TRUE -- Christmas
            WHEN EXTRACT(MONTH FROM date_day) = 1 AND EXTRACT(DAY FROM date_day) = 1 THEN TRUE   -- New Year
            WHEN EXTRACT(MONTH FROM date_day) = 7 AND EXTRACT(DAY FROM date_day) = 4 THEN TRUE   -- Independence Day
            ELSE FALSE 
        END AS is_holiday,
        
        -- dbt metadata
        CURRENT_TIMESTAMP() AS dbt_updated_at,
        CURRENT_TIMESTAMP() AS dbt_created_at
        
    FROM date_spine
)

SELECT * FROM date_dimension
