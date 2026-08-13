{% macro compare_null_values(source_name, source_table, staging_ref, column_name, additional_filters='') %}

  {% set source_query %}
    SELECT
      '{{ source_name }}.{{ source_table }}' as table_name,
      '{{ column_name }}' as column_name,
      COUNT(*) as total_records,
      COUNT({{ column_name }}) as non_null_records,
      COUNT(*) - COUNT({{ column_name }}) as null_records,
      ROUND(100.0 * (COUNT(*) - COUNT({{ column_name }})) / COUNT(*), 2) as null_percentage,
      COUNT(DISTINCT {{ column_name }}) as unique_values
    FROM {{ source(source_name, source_table) }}
    {% if additional_filters %}
    WHERE {{ additional_filters }}
    {% endif %}
  {% endset %}

  {% set staging_query %}
    SELECT
      '{{ staging_ref }}' as table_name,
      '{{ column_name }}' as column_name,
      COUNT(*) as total_records,
      COUNT({{ column_name }}) as non_null_records,
      COUNT(*) - COUNT({{ column_name }}) as null_records,
      ROUND(100.0 * (COUNT(*) - COUNT({{ column_name }})) / COUNT(*), 2) as null_percentage,
      COUNT(DISTINCT {{ column_name }}) as unique_values
    FROM {{ ref(staging_ref) }}
    {% if additional_filters %}
    WHERE {{ additional_filters }}
    {% endif %}
  {% endset %}

  {% if execute %}
    {% set source_results = run_query(source_query) %}
    {% set staging_results = run_query(staging_query) %}

    {{ log("=== NULL VALUE COMPARISON: " ~ column_name ~ " ===", info=True) }}
    {{ log("", info=True) }}

    {% for row in source_results %}
      {{ log("SOURCE (" ~ row[0] ~ "):", info=True) }}
      {{ log("  Total Records: " ~ "{:,}".format(row[2]) if row[2] else "0", info=True) }}
      {{ log("  Non-Null: " ~ "{:,}".format(row[3]) if row[3] else "0", info=True) }}
      {{ log("  Null: " ~ "{:,}".format(row[4]) if row[4] else "0", info=True) }}
      {{ log("  Null %: " ~ row[5] ~ "%", info=True) }}
      {{ log("  Unique Values: " ~ "{:,}".format(row[6]) if row[6] else "0", info=True) }}
      {{ log("", info=True) }}
    {% endfor %}

    {% for row in staging_results %}
      {{ log("STAGING (" ~ row[0] ~ "):", info=True) }}
      {{ log("  Total Records: " ~ "{:,}".format(row[2]) if row[2] else "0", info=True) }}
      {{ log("  Non-Null: " ~ "{:,}".format(row[3]) if row[3] else "0", info=True) }}
      {{ log("  Null: " ~ "{:,}".format(row[4]) if row[4] else "0", info=True) }}
      {{ log("  Null %: " ~ row[5] ~ "%", info=True) }}
      {{ log("  Unique Values: " ~ "{:,}".format(row[6]) if row[6] else "0", info=True) }}
      {{ log("", info=True) }}
    {% endfor %}

    {% if source_results and staging_results %}
      {% set source_nulls = source_results[0][4] %}
      {% set staging_nulls = staging_results[0][4] %}
      {% set null_diff = staging_nulls - source_nulls %}

      {{ log("COMPARISON:", info=True) }}
      {{ log("  Null Difference: " ~ "{:,}".format(null_diff) if null_diff else "0", info=True) }}
      {% if null_diff > 0 %}
        {{ log("  ⚠️  STAGING HAS MORE NULLS (+{:,})".format(null_diff), info=True) }}
      {% elif null_diff < 0 %}
        {{ log("  ✅ STAGING HAS FEWER NULLS ({:,})".format(null_diff), info=True) }}
      {% else %}
        {{ log("  ✅ NULL COUNTS MATCH", info=True) }}
      {% endif %}
    {% endif %}

    {{ log("=== COMPARISON COMPLETE ===", info=True) }}
  {% endif %}

{% endmacro %}

{% macro debug_user_crm_nulls() %}
  {{ compare_null_values('loom_sync', 'transactions', 'stg_transactions', 'user_crm_id') }}
{% endmacro %}
