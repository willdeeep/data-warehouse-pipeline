{% test valid_text_pattern(model, column_name, pattern, where=none) %}
  {#- Generic test for validating text patterns (like city names, usernames, etc.) -#}
  
  select
    {{ column_name }},
    'Invalid pattern detected in {{ column_name }}' as validation_error
  from {{ model }}
  where {{ column_name }} is not null
    and trim({{ column_name }}) != ''
    {% if where %}
    and {{ where }}
    {% endif %}
    and not regexp_contains({{ column_name }}, r'{{ pattern }}')

{% endtest %}
