#!/bin/bash
#
# Quick dbt Test Script
# Runs common dbt operations for development workflow
#

set -e

echo "🚀 Starting dbt development workflow..."

# Run dbt deps to ensure packages are installed
echo "📦 Installing dbt packages..."
./scripts/dbt.sh deps

# Compile the project
echo "🔧 Compiling dbt project..."
./scripts/dbt.sh compile --target prod

# Run dbt models
echo "🏗️  Running dbt models..."
./scripts/dbt.sh run --target prod

# Run dbt tests
echo "🧪 Running dbt tests..."
./scripts/dbt.sh test --target prod

echo "✅ dbt workflow completed successfully!"
echo "🎯 You can now test your DAGs in the Airflow UI"
