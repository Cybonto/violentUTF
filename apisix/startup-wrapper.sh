#!/bin/sh
# APISIX startup wrapper to handle socket cleanup
# This ensures cleanup happens even when container is restarted

echo "🧹 Cleaning up stale socket files..."
rm -f /usr/local/apisix/logs/worker_events.sock 2>/dev/null || true
rm -f /usr/local/apisix/logs/nginx.pid 2>/dev/null || true

echo "🚀 Starting APISIX..."
exec apisix start