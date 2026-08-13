
{# Macro to compare multiple columns between two tables #}
{% macro compare_multiple_columns(source_table, target_table, columns, source_table_type='source', target_table_type='model') %}
  {% for column in columns %}
    {{ log("", info=True) }}
    {{ log("🔍 ANALYZING COLUMN: " ~ column, info=True) }}
    {{ compare_null_values(source_table, target_table, column, source_table_type, target_table_type) }}
  {% endfor %}
{% endmacro %}

{# Comprehensive data quality validation macro #}
{% macro validate_data_quality(table_ref, table_type='model') %}
  {% set query %}
    SELECT
      -- Basic table metrics
      COUNT(*) as total_records,
      COUNT(DISTINCT user_crm_id) as unique_users,
      COUNT(DISTINCT transaction_id) as unique_products,  -- Using transaction_id as identifier
      COUNT(DISTINCT transaction_id) as unique_transactions,

      -- Date range analysis
      MIN(date) as earliest_transaction,
      MAX(date) as latest_transaction,
      COUNT(DISTINCT date) as distinct_days,

      -- Financial metrics
      SUM(transaction_total) as total_revenue,
      AVG(transaction_total) as avg_transaction_amount,
      MIN(transaction_total) as min_transaction_amount,
      MAX(transaction_total) as max_transaction_amount,

      -- Data quality metrics
      COUNT(*) - COUNT(user_crm_id) as null_user_crm_ids,
      COUNT(*) - COUNT(transaction_id) as null_transaction_ids,
      COUNT(*) - COUNT(transaction_total) as null_amounts,

      -- Business logic validation
      SUM(CASE WHEN transaction_total <= 0 THEN 1 ELSE 0 END) as zero_or_negative_amounts,
      SUM(CASE WHEN date > CURRENT_DATE() THEN 1 ELSE 0 END) as future_transactions

    FROM {% if table_type == 'source' %}`{{ table_ref }}`{% else %}{{ ref(table_ref) }}{% endif %}
  {% endset %}

  {% if execute %}
    {% set results = run_query(query) %}

    {{ log("", info=True) }}
    {{ log("=== DATA QUALITY VALIDATION: " ~ table_ref ~ " ===", info=True) }}
    {{ log("", info=True) }}

    {% for row in results %}
      {{ log("📊 BASIC METRICS:", info=True) }}
      {{ log("   Total Records: " ~ "{:,}".format(row[0]), info=True) }}
      {{ log("   Unique Users: " ~ "{:,}".format(row[1]), info=True) }}
      {{ log("   Unique Transactions: " ~ "{:,}".format(row[3]), info=True) }}
      {{ log("", info=True) }}

      {{ log("📅 DATE ANALYSIS:", info=True) }}
      {{ log("   Date Range: " ~ row[4] ~ " to " ~ row[5], info=True) }}
      {{ log("   Days Covered: " ~ "{:,}".format(row[6]), info=True) }}
      {{ log("", info=True) }}

      {{ log("💰 FINANCIAL METRICS:", info=True) }}
      {{ log("   Total Revenue: $" ~ "{:,.2f}".format(row[7]), info=True) }}
      {{ log("   Average Transaction: $" ~ "{:,.2f}".format(row[8]), info=True) }}
      {{ log("   Amount Range: $" ~ "{:,.2f}".format(row[9]) ~ " to $" ~ "{:,.2f}".format(row[10]), info=True) }}
      {{ log("", info=True) }}

      {{ log("🔍 DATA QUALITY ISSUES:", info=True) }}
      {% set quality_issues = 0 %}

      {% if row[11] > 0 %}
        {{ log("   ⚠️  Null user_crm_ids: " ~ "{:,}".format(row[11]), info=True) }}
        {% set quality_issues = quality_issues + 1 %}
      {% endif %}

      {% if row[12] > 0 %}
        {{ log("   ⚠️  Null transaction_ids: " ~ "{:,}".format(row[12]), info=True) }}
        {% set quality_issues = quality_issues + 1 %}
      {% endif %}

      {% if row[13] > 0 %}
        {{ log("   ⚠️  Null transaction amounts: " ~ "{:,}".format(row[13]), info=True) }}
        {% set quality_issues = quality_issues + 1 %}
      {% endif %}

      {% if row[14] > 0 %}
        {{ log("   ⚠️  Zero/negative amounts: " ~ "{:,}".format(row[14]), info=True) }}
        {% set quality_issues = quality_issues + 1 %}
      {% endif %}

      {% if row[15] > 0 %}
        {{ log("   ⚠️  Future transactions: " ~ "{:,}".format(row[15]), info=True) }}
        {% set quality_issues = quality_issues + 1 %}
      {% endif %}

      {% if quality_issues == 0 %}
        {{ log("   ✅ No data quality issues detected!", info=True) }}
      {% else %}
        {{ log("   📝 " ~ quality_issues ~ " data quality issue(s) found", info=True) }}
      {% endif %}

    {% endfor %}

    {{ log("", info=True) }}
    {{ log("=== VALIDATION COMPLETE ===", info=True) }}
    {{ log("", info=True) }}
  {% endif %}
{% endmacro %}

{# Macro to validate schema and column presence #}
{% macro validate_schema_structure(table_ref, expected_columns, table_type='model') %}
  {% set query %}
    SELECT column_name
    FROM `{{ target.project }}.{{ target.schema }}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{{ table_ref }}'
    ORDER BY ordinal_position
  {% endset %}

  {% if execute %}
    {% set results = run_query(query) %}
    {% set actual_columns = [] %}
    {% for row in results %}
      {% do actual_columns.append(row[0]) %}
    {% endfor %}

    {{ log("", info=True) }}
    {{ log("=== SCHEMA VALIDATION: " ~ table_ref ~ " ===", info=True) }}
    {{ log("", info=True) }}

    {{ log("📋 EXPECTED COLUMNS (" ~ expected_columns | length ~ "):", info=True) }}
    {% for col in expected_columns %}
      {{ log("   - " ~ col, info=True) }}
    {% endfor %}
    {{ log("", info=True) }}

    {{ log("📋 ACTUAL COLUMNS (" ~ actual_columns | length ~ "):", info=True) }}
    {% for col in actual_columns %}
      {{ log("   - " ~ col, info=True) }}
    {% endfor %}
    {{ log("", info=True) }}

    {# Check for missing columns #}
    {% set missing_columns = [] %}
    {% for col in expected_columns %}
      {% if col not in actual_columns %}
        {% do missing_columns.append(col) %}
      {% endif %}
    {% endfor %}

    {# Check for extra columns #}
    {% set extra_columns = [] %}
    {% for col in actual_columns %}
      {% if col not in expected_columns %}
        {% do extra_columns.append(col) %}
      {% endif %}
    {% endfor %}

    {{ log("🔍 SCHEMA ANALYSIS:", info=True) }}
    {% if missing_columns | length > 0 %}
      {{ log("   ⚠️  MISSING COLUMNS:", info=True) }}
      {% for col in missing_columns %}
        {{ log("      - " ~ col, info=True) }}
      {% endfor %}
    {% endif %}

    {% if extra_columns | length > 0 %}
      {{ log("   ℹ️  EXTRA COLUMNS:", info=True) }}
      {% for col in extra_columns %}
        {{ log("      - " ~ col, info=True) }}
      {% endfor %}
    {% endif %}

    {% if missing_columns | length == 0 and extra_columns | length == 0 %}
      {{ log("   ✅ Schema matches expected structure perfectly!", info=True) }}
    {% endif %}

    {{ log("", info=True) }}
    {{ log("=== SCHEMA VALIDATION COMPLETE ===", info=True) }}
    {{ log("", info=True) }}
  {% endif %}
{% endmacro %}

{# Macro for row count validation between related tables #}
{% macro validate_relationship_counts(parent_table, child_table, join_key, parent_type='model', child_type='model') %}
  {% set query %}
    WITH parent_counts AS (
      SELECT
        COUNT(*) as total_parent_records,
        COUNT(DISTINCT CAST({{ join_key }} AS STRING)) as unique_parent_keys,
        COUNT(*) - COUNT({{ join_key }}) as null_parent_keys
      FROM {% if parent_type == 'source' %}`{{ parent_table }}`{% else %}{{ ref(parent_table) }}{% endif %}
    ),
    child_counts AS (
      SELECT
        COUNT(*) as total_child_records,
        COUNT(DISTINCT CAST({{ join_key }} AS STRING)) as unique_child_keys,
        COUNT(*) - COUNT({{ join_key }}) as null_child_keys
      FROM {% if child_type == 'source' %}`{{ child_table }}`{% else %}{{ ref(child_table) }}{% endif %}
    ),
    orphaned_children AS (
      SELECT COUNT(*) as orphaned_records
      FROM {% if child_type == 'source' %}`{{ child_table }}`{% else %}{{ ref(child_table) }}{% endif %} c
      LEFT JOIN {% if parent_type == 'source' %}`{{ parent_table }}`{% else %}{{ ref(parent_table) }}{% endif %} p
        ON CAST(c.{{ join_key }} AS STRING) = CAST(p.{{ join_key }} AS STRING)
      WHERE p.{{ join_key }} IS NULL
        AND c.{{ join_key }} IS NOT NULL
    )
    SELECT
      p.total_parent_records,
      p.unique_parent_keys,
      p.null_parent_keys,
      c.total_child_records,
      c.unique_child_keys,
      c.null_child_keys,
      o.orphaned_records
    FROM parent_counts p
    CROSS JOIN child_counts c
    CROSS JOIN orphaned_children o
  {% endset %}

  {% if execute %}
    {% set results = run_query(query) %}

    {{ log("", info=True) }}
    {{ log("=== RELATIONSHIP VALIDATION ===", info=True) }}
    {{ log("Parent: " ~ parent_table ~ " | Child: " ~ child_table ~ " | Key: " ~ join_key, info=True) }}
    {{ log("", info=True) }}

    {% for row in results %}
      {{ log("👥 PARENT TABLE (" ~ parent_table ~ "):", info=True) }}
      {{ log("   Total Records: " ~ "{:,}".format(row[0]), info=True) }}
      {{ log("   Unique Keys: " ~ "{:,}".format(row[1]), info=True) }}
      {{ log("   Null Keys: " ~ "{:,}".format(row[2]), info=True) }}
      {{ log("", info=True) }}

      {{ log("👶 CHILD TABLE (" ~ child_table ~ "):", info=True) }}
      {{ log("   Total Records: " ~ "{:,}".format(row[3]), info=True) }}
      {{ log("   Unique Keys: " ~ "{:,}".format(row[4]), info=True) }}
      {{ log("   Null Keys: " ~ "{:,}".format(row[5]), info=True) }}
      {{ log("", info=True) }}

      {{ log("🔗 RELATIONSHIP ANALYSIS:", info=True) }}
      {% if row[6] > 0 %}
        {{ log("   ⚠️  Orphaned Records: " ~ "{:,}".format(row[6]), info=True) }}
        {{ log("   (Child records with no matching parent)", info=True) }}
      {% else %}
        {{ log("   ✅ No orphaned records found", info=True) }}
      {% endif %}

      {% set referential_integrity = (row[6] == 0) %}
      {% if referential_integrity %}
        {{ log("   ✅ Referential integrity maintained", info=True) }}
      {% else %}
        {{ log("   ⚠️  Referential integrity issues detected", info=True) }}
      {% endif %}

    {% endfor %}

    {{ log("", info=True) }}
    {{ log("=== RELATIONSHIP VALIDATION COMPLETE ===", info=True) }}
    {{ log("", info=True) }}
  {% endif %}
{% endmacro %}
