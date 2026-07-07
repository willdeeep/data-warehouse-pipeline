#!/bin/bash
#
# dbt Helper Script for Container-based Development
# Usage: ./scripts/dbt.sh <command> [options]
#
# Examples:
#   ./scripts/dbt.sh run --models stg_users
#   ./scripts/dbt.sh test
#   ./scripts/dbt.sh compile --target prod
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[dbt-container]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[dbt-container]${NC} $1"
}

print_error() {
    echo -e "${RED}[dbt-container]${NC} $1"
}

# Check if Astronomer is running
if ! astro dev ps &>/dev/null; then
    print_error "Astronomer dev environment is not running!"
    print_status "Starting Astronomer dev environment..."
    astro dev start
    sleep 10
fi

# Get the scheduler container ID
SCHEDULER_CONTAINER=$(astro dev ps | grep scheduler | awk '{print $1}')

if [ -z "$SCHEDULER_CONTAINER" ]; then
    print_error "Could not find Airflow scheduler container"
    print_status "Available containers:"
    astro dev ps
    exit 1
fi

print_status "Running dbt command in container: $SCHEDULER_CONTAINER"
print_status "Command: dbt $*"

# Execute dbt command in the scheduler container
docker exec -it "$SCHEDULER_CONTAINER" bash -c "
    cd /usr/local/airflow/pipeline/dbt && 
    dbt $* --profiles-dir .
"

# Check exit code
if [ $? -eq 0 ]; then
    print_status "dbt command completed successfully"
else
    print_error "dbt command failed"
    exit 1
fi
