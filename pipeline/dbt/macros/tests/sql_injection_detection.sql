{% test sql_injection_detection(model, column_name, where=none) %}
  {#- Generic test for SQL injection detection with consolidated patterns -#}

  select
    {{ column_name }},
    'Potential SQL injection pattern detected' as security_warning
  from {{ model }}
  where {{ column_name }} is not null
    and trim({{ column_name }}) != ''
    {% if where %}
    and {{ where }}
    {% endif %}
    and (
      REGEXP_CONTAINS(UPPER({{ column_name }}), r'(SELECT|DROP|DELETE|INSERT|UPDATE|UNION|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE)')
      OR REGEXP_CONTAINS({{ column_name }}, r'(<script|javascript:|onload=|onerror=|xp_|sp_)')
      OR REGEXP_CONTAINS({{ column_name }}, r"'")
      OR REGEXP_CONTAINS({{ column_name }}, r'\"')
      OR REGEXP_CONTAINS({{ column_name }}, r';')
      OR REGEXP_CONTAINS({{ column_name }}, r'<')
      OR REGEXP_CONTAINS({{ column_name }}, r'>')
      OR REGEXP_CONTAINS({{ column_name }}, r'(--|/\*|\*/)')
    )

{% endtest %}
