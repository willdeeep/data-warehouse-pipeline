#!/bin/bash
# Live dependency updater for Docker containers

set -e

CONTAINER_NAME="${1:-airflow_webserver_dev}"
REQUIREMENTS_FILE="${2:-requirements.txt}"

echo "🔄 Live updating Python dependencies in container: $CONTAINER_NAME"

if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Container $CONTAINER_NAME is not running"
    exit 1
fi

echo "📦 Installing new dependencies from $REQUIREMENTS_FILE..."
docker exec "$CONTAINER_NAME" bash -c "
    pip install --no-cache-dir -r /tmp/$REQUIREMENTS_FILE
    echo '✅ Dependencies updated successfully!'
    echo '🔄 Restarting Airflow services...'
    
    # Restart webserver gracefully
    if pgrep -f 'airflow webserver' > /dev/null; then
        pkill -f 'airflow webserver'
        sleep 2
        airflow webserver --daemon
    fi
"

echo "✅ Live dependency update completed!"
echo "🌐 Airflow should be available shortly at http://localhost:8080"
