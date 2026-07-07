{% macro test_custom_schema() %}
  {{ log("", info=True) }}
  {{ log("🏗️  ==============================================", info=True) }}
  {{ log("🔧 TESTING CUSTOM SCHEMA CONFIGURATION", info=True) }}
  {{ log("🏗️  ==============================================", info=True) }}
  {{ log("", info=True) }}
  
  {{ log("🎯 TARGET ENVIRONMENT: " ~ target.name, info=True) }}
  {{ log("📂 DEFAULT SCHEMA: " ~ target.schema, info=True) }}
  {{ log("", info=True) }}
  
  {# Test different model types and their expected schema routing #}
  {% set test_models = [
    {
      'name': 'staging_model',
      'path': ['staging', 'stg_transactions'],
      'expected_schema': 'dev_warehouse' if target.name == 'prod' else target.schema ~ '_staging'
    },
    {
      'name': 'intermediate_model', 
      'path': ['intermediate', 'fact_sessions'],
      'expected_schema': 'dev_warehouse' if target.name == 'prod' else target.schema ~ '_intermediate'
    },
    {
      'name': 'marts_model',
      'path': ['marts', 'transactions_mart'],
      'expected_schema': 'warehouse' if target.name == 'prod' else target.schema ~ '_marts'
    },
    {
      'name': 'dim_model',
      'path': ['dim', 'dim_users'],
      'expected_schema': target.schema if target.name == 'prod' else target.schema ~ '_dim'
    }
  ] %}
  
  {% for model in test_models %}
    {{ log("📋 TESTING MODEL: " ~ model.name, info=True) }}
    {{ log("   Path: " ~ model.path | join('/'), info=True) }}
    {{ log("   Expected Schema: " ~ model.expected_schema, info=True) }}
    
    {# Create a mock node object for testing #}
    {% set mock_node = {'fqn': model.path} %}
    
    {# Test with no custom schema #}
    {% set result_no_custom = generate_schema_name(none, mock_node) %}
    {{ log("   Result (no custom): " ~ result_no_custom, info=True) }}
    
    {# Test with custom schema based on path #}
    {% if 'staging' in model.path %}
      {% set custom_schema = 'staging' %}
    {% elif 'intermediate' in model.path %}
      {% set custom_schema = 'intermediate' %}
    {% elif 'marts' in model.path %}
      {% set custom_schema = 'marts' %}
    {% elif 'dim' in model.path %}
      {% set custom_schema = 'dim' %}
    {% else %}
      {% set custom_schema = 'other' %}
    {% endif %}
    
    {% set result_with_custom = generate_schema_name(custom_schema, mock_node) %}
    {{ log("   Result (with custom): " ~ result_with_custom, info=True) }}
    
    {% if target.name == 'prod' %}
      {% if 'staging' in model.path or 'intermediate' in model.path %}
        {% set expected = 'dev_warehouse' %}
      {% elif 'marts' in model.path %}
        {% set expected = 'warehouse' %}
      {% else %}
        {% set expected = custom_schema %}
      {% endif %}
      
      {% set result_clean = result_with_custom | trim %}
      {% if result_clean == expected %}
        {{ log("   ✅ PRODUCTION ROUTING CORRECT", info=True) }}
      {% else %}
        {{ log("   ❌ PRODUCTION ROUTING INCORRECT - Expected: " ~ expected ~ ", Got: " ~ result_clean, info=True) }}
      {% endif %}
    {% else %}
      {{ log("   ℹ️  Development environment - using default behavior", info=True) }}
    {% endif %}
    
    {{ log("", info=True) }}
  {% endfor %}
  
  {{ log("🔍 CUSTOM SCHEMA ROUTING SUMMARY:", info=True) }}
  {{ log("", info=True) }}
  
  {% if target.name == 'prod' %}
    {{ log("📊 PRODUCTION ENVIRONMENT ROUTING:", info=True) }}
    {{ log("   • staging/* → dev_warehouse", info=True) }}
    {{ log("   • intermediate/* → dev_warehouse", info=True) }}
    {{ log("   • marts/* → warehouse", info=True) }}
    {{ log("   • other/* → custom_schema_name", info=True) }}
  {% else %}
    {{ log("🛠️  DEVELOPMENT ENVIRONMENT ROUTING:", info=True) }}
    {{ log("   • All models → " ~ target.schema ~ "_custom_schema", info=True) }}
  {% endif %}
  
  {{ log("", info=True) }}
  {{ log("✅ Custom schema configuration test complete!", info=True) }}
  {{ log("", info=True) }}
  
{% endmacro %}
