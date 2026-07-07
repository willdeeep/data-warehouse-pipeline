#!/bin/bash
# =============================================================================
# Airflow User Management Script
# =============================================================================
# This script provides commands to create different types of Airflow users

echo "Airflow User Creation Commands"
echo "=============================="

echo ""
echo "1. Create Admin User:"
echo "docker exec airflow_webserver airflow users create \\"
echo "  --username admin \\"
echo "  --firstname Admin \\"
echo "  --lastname User \\"
echo "  --role Admin \\"
echo "  --email admin@example.com \\"
echo "  --password admin123"

echo ""
echo "2. Create Viewer User (read-only access):"
echo "docker exec airflow_webserver airflow users create \\"
echo "  --username viewer \\"
echo "  --firstname Viewer \\"
echo "  --lastname User \\"
echo "  --role Viewer \\"
echo "  --email viewer@example.com \\"
echo "  --password viewer123"

echo ""
echo "3. Create Op User (can trigger DAGs):"
echo "docker exec airflow_webserver airflow users create \\"
echo "  --username operator \\"
echo "  --firstname Operator \\"
echo "  --lastname User \\"
echo "  --role Op \\"
echo "  --email operator@example.com \\"
echo "  --password operator123"

echo ""
echo "4. List all users:"
echo "docker exec airflow_webserver airflow users list"

echo ""
echo "5. Delete a user:"
echo "docker exec airflow_webserver airflow users delete --username <username>"

echo ""
echo "Available Roles:"
echo "- Admin: Full access to all Airflow features"
echo "- Op: Can view and trigger DAGs, view task logs"
echo "- Viewer: Read-only access to DAGs and task instances"
echo "- User: Limited access"
echo "- Public: Minimal access"

echo ""
echo "Current Admin User Created:"
echo "- Username: admin"
echo "- Password: admin123"
echo "- URL: http://localhost:8080"
