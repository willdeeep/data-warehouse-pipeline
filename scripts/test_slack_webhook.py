"""
Test script to verify Slack webhook functionality locally
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"❌ .env file not found at {env_path}")

def test_slack_notification():
    """Test sending a Slack notification"""

    # Get webhook URL from environment
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL not found in environment variables")
        print("Make sure you have set it in your .env file")
        return False

    print(f"✅ Found webhook URL: {webhook_url[:50]}...")

    # Create test message
    test_message = {
        "text": "🧪 Test Notification from Local Environment",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🧪 Airflow Slack Integration Test"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Environment:* Local Development"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Test Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:* Testing Slack Integration ✅"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Test message: verifying Slack webhook integration working correctly the local Airflow env."
                }
            }
        ]
    }

    try:
        print("📤 Sending test message to Slack...")
        response = requests.post(
            webhook_url,
            data=json.dumps(test_message),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ SUCCESS: Test message sent to Slack successfully!")
            print("Check your Slack channel for the test message.")
            return True
        else:
            print(f"❌ FAILED: Slack API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Error sending message: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Slack Webhook Integration")
    print("=" * 50)

    # Load environment variables
    load_env_file()

    success = test_slack_notification()
    print("=" * 50)
    if success:
        print("🎉 Slack integration is working! You can now use it in your DAGs.")
    else:
        print("💥 Slack integration test failed. Please check your configuration.")
