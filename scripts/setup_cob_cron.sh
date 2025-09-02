#!/bin/bash

# Setup COB Report Scheduling Cron Job
# This script sets up a system cron job to check for scheduled reports every minute

set -e

# Configuration
CRON_USER=${CRON_USER:-root}
API_URL=${VIOLENTUTF_API_URL:-http://localhost:8000}
CRON_ENDPOINT="${API_URL}/api/v1/reports/internal/check-schedules"

echo "🔄 Setting up COB Report scheduling cron job..."

# Create cron job content
CRON_CONTENT="# ViolentUTF COB Report Scheduler
# Check for scheduled reports every minute
# NOTE: This requires API authentication - set VIOLENTUTF_API_KEY environment variable
* * * * * [ -n \"\$VIOLENTUTF_API_KEY\" ] && curl -s -X POST \"${CRON_ENDPOINT}\" -H \"Content-Type: application/json\" -H \"Authorization: Bearer \$VIOLENTUTF_API_KEY\" >/dev/null 2>&1 || logger \"COB cron: Missing VIOLENTUTF_API_KEY\"
"

# Cron file path
CRON_FILE="/etc/cron.d/violentutf-cob"

echo "📝 Creating cron file: ${CRON_FILE}"

# Create the cron file (requires sudo)
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script requires sudo privileges to create system cron jobs"
    echo "🔄 Attempting to create cron job with sudo..."
    echo "${CRON_CONTENT}" | sudo tee "${CRON_FILE}" > /dev/null
    sudo chmod 644 "${CRON_FILE}"
    sudo chown root:root "${CRON_FILE}"
else
    echo "${CRON_CONTENT}" > "${CRON_FILE}"
    chmod 644 "${CRON_FILE}"
    chown root:root "${CRON_FILE}"
fi

echo "✅ COB Report cron job created successfully"
echo "📍 Endpoint: ${CRON_ENDPOINT}"
echo "📅 Schedule: Every minute"

# Verify cron job
echo "🔍 Verifying cron job installation..."
if [ -f "${CRON_FILE}" ]; then
    echo "✅ Cron file exists: ${CRON_FILE}"
    cat "${CRON_FILE}"
else
    echo "❌ Cron file not found: ${CRON_FILE}"
    exit 1
fi

# Test endpoint accessibility (optional)
echo "🔍 Testing endpoint accessibility..."
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${CRON_ENDPOINT}" -H "Content-Type: application/json" || echo "000")
    if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "401" ]; then
        echo "✅ Endpoint is accessible (HTTP ${HTTP_CODE})"
        if [ "${HTTP_CODE}" = "401" ]; then
            echo "ℹ️  Note: 401 is expected for unauthenticated requests"
        fi
    else
        echo "⚠️  Endpoint returned HTTP ${HTTP_CODE} - ensure ViolentUTF API is running"
    fi
else
    echo "⚠️  curl not available - cannot test endpoint"
fi

echo "🚀 COB Report scheduling is now active!"
echo ""
echo "⚠️  IMPORTANT: Set up authentication for the cron job:"
echo "   1. Create an API key for the cron service account"
echo "   2. Set VIOLENTUTF_API_KEY environment variable in /etc/environment"
echo "   3. Or configure the API key in the cron job directly (less secure)"
echo ""
echo "📚 For more information, see: /docs/guides/COB_Report_Scheduling.md"
