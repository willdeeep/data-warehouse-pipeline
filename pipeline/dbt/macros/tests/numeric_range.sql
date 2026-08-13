{% test numeric_range(model, column_name, min_value, max_value, where=none) %}
  {#- Generic test for validating that numeric values fall within a specified range -#}

  select
    {{ column_name }},
    'Value must be between {{ min_value }} and {{ max_value }}' as validation_error
  from {{ model }}
  where {{ column_name }} is not null
    {% if where %}
    and {{ where }}
    {% endif %}
    and (SAFE_CAST({{ column_name }} AS INT64) < {{ min_value }} OR SAFE_CAST({{ column_name }} AS INT64) > {{ max_value }})

{% endtest %}
