{% macro validate_row_counts(models_list=none) %}
  {# Enhanced row count validation with flexible model selection #}

  {% if models_list is none %}
    {% set models_to_check = [
      'stg_transactions',
      'fct_transactions',
      'dim_users',
      'dim_products',
      'dim_date',
      'rpt_transactions'
    ] %}
  {% else %}
    {% set models_to_check = models_list %}
  {% endif %}

  {{ log("", info=True) }}
  {{ log("=== MULTI-MODEL ROW COUNT VALIDATION ===", info=True) }}
  {{ log("Models to check: " ~ models_to_check | join(', '), info=True) }}
  {{ log("", info=True) }}

  {% for model in models_to_check %}
    {% set query %}
      SELECT
        '{{ model }}' as model_name,
        COUNT(*) as row_count,
        CURRENT_TIMESTAMP() as checked_at
      FROM {{ ref(model) }}
    {% endset %}

    {% set results = run_query(query) %}
    {% if results %}
      {% for row in results %}
        {{ log("✅ " ~ row[0] ~ ": " ~ "{:,}".format(row[1]) ~ " rows", info=True) }}
      {% endfor %}
    {% else %}
      {{ log("❌ " ~ model ~ ": FAILED TO RETRIEVE COUNT", info=True) }}
    {% endif %}
  {% endfor %}

  {{ log("", info=True) }}
  {{ log("=== ROW COUNT VALIDATION COMPLETE ===", info=True) }}
  {{ log("", info=True) }}
{% endmacro %}
