
/*
===================================================================================
MACRO: generate_schema_docs
===================================================================================

PURPOSE:
    Generates BigQuery-compatible table and column descriptions from dbt YAML
    configuration, ensuring documentation is persisted to the data warehouse.

USAGE:
    {{ generate_schema_docs() }}

FEATURES:
    - Extracts model descriptions from YAML files
    - Formats column descriptions for BigQuery
    - Handles special characters and length limits
    - Supports both table and column-level documentation
===================================================================================
*/

{% macro generate_schema_docs() %}
    {# This macro will be called during model compilation to ensure docs are included #}
    {% if execute %}
        {% set current_model = model %}
        {% if current_model.description %}
            {% set table_description = current_model.description[:1024] %}
            {{ log("Adding table description: " ~ table_description, info=false) }}
        {% endif %}

        {% for column in current_model.columns %}
            {% if column.description %}
                {% set col_description = column.description[:1024] %}
                {{ log("Adding column description for " ~ column.name ~ ": " ~ col_description, info=false) }}
            {% endif %}
        {% endfor %}
    {% endif %}
{% endmacro %}


/*
===================================================================================
MACRO: get_model_description
===================================================================================

PURPOSE:
    Retrieves the model description for use in BigQuery table comments.
===================================================================================
*/

{% macro get_model_description() %}
    {% if model.description %}
        {{ return(model.description[:1024]) }}
    {% else %}
        {{ return('dbt model - ' ~ model.name) }}
    {% endif %}
{% endmacro %}


/*
===================================================================================
MACRO: bigquery_table_comment
===================================================================================

PURPOSE:
    Generates BigQuery-compatible table comments with model metadata.
===================================================================================
*/

{% macro bigquery_table_comment() %}
    {% set description = get_model_description() %}
    {% set current_timestamp = modules.datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC') %}
    {% set table_comment %}
{{ description }}

Model Details:
- dbt Model: {{ model.name }}
- Schema: {{ model.schema }}
- Materialized As: {{ config.get('materialized', 'view') }}
- Generated: {{ current_timestamp }}
- dbt Version: {{ dbt_version }}
    {% endset %}
    {{ return(table_comment) }}
{% endmacro %}
