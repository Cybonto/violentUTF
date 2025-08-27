#!/bin/bash

# Configure APISIX routes for orchestrator endpoints

APISIX_ADMIN_URL="http://localhost:9180"
API_UPSTREAM="http://host.docker.internal:8000"

# Load admin key from environment
if [ -f .env ]; then
    APISIX_ADMIN_KEY=$(grep "APISIX_ADMIN_KEY=" .env | cut -d'=' -f2)
fi

if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo "Error: APISIX_ADMIN_KEY not found in .env file"
    exit 1
fi

echo "Configuring orchestrator API routes in APISIX..."

# Orchestrator Type Discovery
curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/orchestrator-types" \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -d '{
    "uri": "/api/v1/orchestrators/types*",
    "methods": ["GET"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "'${API_UPSTREAM}'": 1
      }
    },
    "plugins": {
      "jwt-auth": {},
      "response-headers": {
        "X-API-Gateway": "APISIX"
      }
    }
  }'

echo ""

# Orchestrator Configuration Management
curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/orchestrator-config" \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -d '{
    "uri": "/api/v1/orchestrators",
    "methods": ["GET", "POST"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "'${API_UPSTREAM}'": 1
      }
    },
    "plugins": {
      "jwt-auth": {},
      "response-headers": {
        "X-API-Gateway": "APISIX"
      }
    }
  }'

echo ""

# Individual Orchestrator Operations
curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/orchestrator-individual" \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -d '{
    "uri": "/api/v1/orchestrators/*",
    "methods": ["GET", "PUT", "DELETE", "POST"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "'${API_UPSTREAM}'": 1
      }
    },
    "plugins": {
      "jwt-auth": {},
      "response-headers": {
        "X-API-Gateway": "APISIX"
      }
    }
  }'

echo ""

echo "Orchestrator API routes configured successfully!"
echo ""
echo "Available routes:"
echo "  GET  /api/v1/orchestrators/types"
echo "  GET  /api/v1/orchestrators/types/{type}"
echo "  GET  /api/v1/orchestrators"
echo "  POST /api/v1/orchestrators"
echo "  GET  /api/v1/orchestrators/{id}"
echo "  POST /api/v1/orchestrators/{id}/execute"
echo "  GET  /api/v1/orchestrators/executions/{id}/results"
echo "  GET  /api/v1/orchestrators/{id}/memory"
echo "  GET  /api/v1/orchestrators/{id}/scores"
echo "  DELETE /api/v1/orchestrators/{id}"
