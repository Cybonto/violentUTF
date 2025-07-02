#!/usr/bin/env bash
# openapi_setup.sh - OpenAPI/Swagger documentation routes and configuration

# Function to configure OpenAPI documentation routes
configure_openapi_routes() {
    echo "Configuring OpenAPI documentation routes..."
    
    # Create FastAPI docs routes
    create_fastapi_docs_routes
    
    # Verify the routes are accessible
    verify_docs_accessibility
    
    echo "✅ OpenAPI routes configuration completed"
    return 0
}

# Function to create FastAPI docs routes
create_fastapi_docs_routes() {
    echo "Creating FastAPI documentation routes..."
    
    # Load APISIX configuration
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi
    
    local admin_key="${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}"
    local apisix_admin_url="http://localhost:9180"
    
    # Create /api/docs route
    cat > /tmp/fastapi-docs-route.json <<EOF
{
    "uri": "/api/docs",
    "name": "violentutf-docs",
    "methods": ["GET"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/docs"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "max_age": 3600,
            "allow_credential": true
        }
    }
}
EOF
    
    # Create docs route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/violentutf-docs" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-docs-route.json)
    
    local status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ FastAPI docs route created successfully."
    else
        echo "⚠️  Warning: Failed to create FastAPI docs route. Status: $status_code"
    fi
    
    # Create /api/redoc route
    cat > /tmp/fastapi-redoc-route.json <<EOF
{
    "uri": "/api/redoc",
    "name": "violentutf-redoc",
    "methods": ["GET"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/redoc"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "max_age": 3600,
            "allow_credential": true
        }
    }
}
EOF
    
    # Create redoc route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/violentutf-redoc" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-redoc-route.json)
    
    local status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ FastAPI redoc route created successfully."
    else
        echo "⚠️  Warning: Failed to create FastAPI redoc route. Status: $status_code"
    fi
    
    # Clean up temp files
    rm -f /tmp/fastapi-docs-route.json /tmp/fastapi-redoc-route.json
    
    echo "FastAPI documentation routes configured."
}

# Function to verify documentation accessibility
verify_docs_accessibility() {
    echo "Verifying documentation accessibility..."
    
    local test_count=0
    local passed_count=0
    
    # Test docs endpoint
    if curl -s http://localhost:9080/api/docs >/dev/null 2>&1; then
        echo "✅ FastAPI docs endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ FastAPI docs endpoint is not accessible"
    fi
    test_count=$((test_count + 1))
    
    # Test redoc endpoint
    if curl -s http://localhost:9080/api/redoc >/dev/null 2>&1; then
        echo "✅ FastAPI redoc endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ FastAPI redoc endpoint is not accessible"
    fi
    test_count=$((test_count + 1))
    
    # Test OpenAPI JSON endpoint
    if curl -s http://localhost:9080/api/openapi.json >/dev/null 2>&1; then
        echo "✅ OpenAPI JSON endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ OpenAPI JSON endpoint is not accessible"
    fi
    test_count=$((test_count + 1))
    
    echo "📊 Documentation accessibility: $passed_count/$test_count endpoints accessible"
    
    if [ $passed_count -eq $test_count ]; then
        return 0
    else
        return 1
    fi
}