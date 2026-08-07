{% macro generate_int_surrogate_key(field_list) -%}
    -- Deterministic signed INT64 surrogate key (conformed): same inputs -> same key, no lookup join.
    -- Integer analogue of dbt_utils.generate_surrogate_key (which yields a 32-char MD5 hex string);
    -- cheaper to store/join in BigQuery. NULLs map to a distinct placeholder to avoid ambiguity.
    -- (BigQuery has no CONCAT_WS; ARRAY_TO_STRING joins the coalesced parts with a '|' separator.)
    farm_fingerprint(array_to_string([
        {%- for field in field_list %}
        coalesce(cast({{ field }} as string), '_dbt_null_'){{ "," if not loop.last }}
        {%- endfor %}
    ], '|'))
{%- endmacro %}
