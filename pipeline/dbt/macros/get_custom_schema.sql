
{#
Custom schema generation macro for production deployment routing.

This macro automatically routes models to appropriate schemas based on their layer:
- staging/core models → dev_warehouse (for development/testing)
- marts models → warehouse (for production consumption)
- Other models → default schema behavior

This ensures clean separation between development artifacts and production-ready data products.
#}

{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}

    {%- if custom_schema_name is none -%}
        {# No custom schema specified, use target schema #}
        {{ default_schema }}

    {%- elif target.name == 'prod' -%}
        {# Production environment - route based on model path #}

        {%- set model_path = node.fqn -%}

        {%- if 'staging' in model_path or 'core' in model_path -%}
            {# Staging and core models go to dev_warehouse #}
            dev_warehouse

        {%- elif 'marts' in model_path -%}
            {# Marts models go to main warehouse schema #}
            warehouse

        {%- else -%}
            {# Other models use custom schema if provided #}
            {{ custom_schema_name | trim }}

        {%- endif -%}

    {%- else -%}
        {# Development environment - use default behavior #}
        {# This typically results in: target_schema_custom_schema #}
        {{ default_schema }}_{{ custom_schema_name | trim }}

    {%- endif -%}

{%- endmacro %}
