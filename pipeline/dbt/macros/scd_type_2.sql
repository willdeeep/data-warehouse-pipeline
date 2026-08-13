{% macro scd_type_2(
    target_relation,
    unique_key,
    updated_at_column=none,
    check_columns=none,
    invalidate_hard_deletes=true
) %}

/*
Slowly Changing Dimension Type 2 Implementation

This macro implements SCD Type 2 logic to track historical changes in dimension data.
It creates new records when changes are detected and maintains valid_from/valid_to dates.

Parameters:
- target_relation: The target table/model relation
- unique_key: The business key to identify unique records
- updated_at_column: Column to check for freshness (optional)
- check_columns: List of columns to monitor for changes (default: all except metadata)
- invalidate_hard_deletes: Whether to mark deleted records as invalid (default: true)
*/

    {%- set target_columns = adapter.get_columns_in_relation(target_relation) -%}
    {%- set target_cols_csv = target_columns | map(attribute='quoted') | join(', ') -%}

    {%- if check_columns is none -%}
        {%- set check_columns = target_columns | map(attribute='name') | reject('in', ['valid_from', 'valid_to', 'is_current', 'dbt_scd_id', 'dbt_updated_at', 'dbt_created_at']) | list -%}
    {%- endif -%}

    {%- set check_cols_csv = check_columns | join(', ') -%}

    WITH source_data AS (
        SELECT
            *,
            CURRENT_TIMESTAMP() AS dbt_updated_at,
            {{ dbt_utils.surrogate_key([unique_key]) }} AS dbt_scd_id
        FROM ({{ this }})
    ),

    {% if is_incremental() %}

    target_data AS (
        SELECT
            *
        FROM {{ target_relation }}
        WHERE is_current = TRUE
    ),

    -- Identify new and changed records
    source_with_changes AS (
        SELECT
            s.*,
            CASE
                WHEN t.{{ unique_key }} IS NULL THEN 'insert'
                WHEN {{ dbt_utils.generate_surrogate_key(check_columns) }} !=
                     t.{{ unique_key }}_checksum
                THEN 'update'
                ELSE 'no_change'
            END AS change_type
        FROM source_data s
        LEFT JOIN (
            SELECT
                *,
                {{ dbt_utils.generate_surrogate_key(check_columns) }} AS {{ unique_key }}_checksum
            FROM target_data
        ) t ON s.{{ unique_key }} = t.{{ unique_key }}
    ),

    -- Records to insert (new and changed)
    records_to_insert AS (
        SELECT
            *,
            CURRENT_TIMESTAMP() AS valid_from,
            CAST(NULL AS TIMESTAMP) AS valid_to,
            TRUE AS is_current
        FROM source_with_changes
        WHERE change_type IN ('insert', 'update')
    ),

    -- Historical records (invalidate changed records)
    historical_records AS (
        SELECT
            t.*,
            CASE
                WHEN s.change_type = 'update' THEN FALSE
                ELSE t.is_current
            END AS is_current,
            CASE
                WHEN s.change_type = 'update' THEN CURRENT_TIMESTAMP()
                ELSE t.valid_to
            END AS valid_to
        FROM {{ target_relation }} t
        LEFT JOIN source_with_changes s ON t.{{ unique_key }} = s.{{ unique_key }}
        WHERE NOT (s.change_type = 'update' AND t.is_current = TRUE)
    ),

    final AS (
        SELECT * FROM historical_records
        UNION ALL
        SELECT * FROM records_to_insert
    )

    {% else %}

    -- Initial load
    final AS (
        SELECT
            *,
            CURRENT_TIMESTAMP() AS valid_from,
            CAST(NULL AS TIMESTAMP) AS valid_to,
            TRUE AS is_current
        FROM source_data
    )

    {% endif %}

    SELECT * FROM final

{% endmacro %}
