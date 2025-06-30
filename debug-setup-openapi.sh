#!/bin/bash
# Debug script to test the exact setup_macos.sh OpenAPI logic

echo "🔍 Testing setup_macos.sh OpenAPI logic"
echo "======================================"

# Load environment
source ai-tokens.env
source apisix/.env

echo "Environment loaded:"
echo "  OPENAPI_ENABLED: $OPENAPI_ENABLED"
echo "  OPENAPI_1_ENABLED: $OPENAPI_1_ENABLED"
echo "  APISIX_ADMIN_KEY: ${APISIX_ADMIN_KEY:0:8}..."

# Create cache directory like the setup script
cache_dir="/tmp/violentutf_openapi_cache"
mkdir -p "$cache_dir"

# Test the exact fetch and parse logic from setup_macos.sh
provider_id="$OPENAPI_1_ID"
provider_name="$OPENAPI_1_NAME"
base_url="$OPENAPI_1_BASE_URL"
spec_path="$OPENAPI_1_SPEC_PATH"
auth_type="$OPENAPI_1_AUTH_TYPE"
auth_value="$OPENAPI_1_AUTH_TOKEN"

echo ""
echo "Testing provider: $provider_name ($provider_id)"
echo "Base URL: $base_url"
echo "Spec path: $spec_path"

# Test fetch_openapi_spec function (extract from setup_macos.sh)
spec_file="$cache_dir/${provider_id}_spec.json"

echo ""
echo "🔧 Fetching OpenAPI spec..."
curl_args=(-s -f)

# Add SSL bypass (like our fixed version)
if ! curl -s --connect-timeout 5 --max-time 10 "${base_url%/}${spec_path}" > /dev/null 2>&1; then
    echo "⚠️  SSL connectivity issue detected, using insecure connection..."
    curl_args+=(-k)
fi

# Add authentication
curl_args+=(-H "Authorization: Bearer $auth_value")

# Fetch the spec
full_url="${base_url%/}/${spec_path#/}"
if curl "${curl_args[@]}" "$full_url" -o "$spec_file"; then
    echo "✅ Successfully fetched OpenAPI spec"
    echo "   Size: $(wc -c < "$spec_file") bytes"
else
    echo "❌ Failed to fetch OpenAPI spec"
    exit 1
fi

# Test parse_openapi_endpoints function (exact code from setup_macos.sh)
echo ""
echo "🔧 Parsing OpenAPI endpoints..."
endpoints_file="$cache_dir/${provider_id}_endpoints.json"

if python3 - "$spec_file" "$provider_id" > "$endpoints_file" << 'EOF'
import json
import yaml
import sys

try:
    spec_file = sys.argv[1]
    provider_id = sys.argv[2]
    
    # Load the spec
    with open(spec_file, 'r') as f:
        content = f.read()
        try:
            spec = json.loads(content)
        except:
            spec = yaml.safe_load(content)
    
    # Extract base information
    servers = spec.get('servers', [])
    base_path = servers[0].get('url', '') if servers else ''
    
    # Extract paths and operations
    paths = spec.get('paths', {})
    endpoints = []
    
    for path, path_item in paths.items():
        # Skip if path item is a reference
        if isinstance(path_item, dict) and '$ref' not in path_item:
            for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                if method in path_item:
                    operation = path_item[method]
                    
                    # Generate unique operation ID if not provided
                    op_id = operation.get('operationId', f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}")
                    
                    # Extract operation details
                    endpoint = {
                        'path': path,
                        'method': method.upper(),
                        'operationId': op_id,
                        'summary': operation.get('summary', ''),
                        'description': operation.get('description', ''),
                        'tags': operation.get('tags', []),
                        'security': operation.get('security', spec.get('security', [])),
                        'parameters': operation.get('parameters', []),
                        'requestBody': operation.get('requestBody', {}),
                        'responses': operation.get('responses', {})
                    }
                    
                    # Check if this looks like an AI/chat endpoint
                    is_ai_endpoint = any(keyword in path.lower() or keyword in endpoint['summary'].lower() 
                                       for keyword in ['chat', 'completion', 'generate', 'predict', 'inference', 'embedding'])
                    endpoint['is_ai_endpoint'] = is_ai_endpoint
                    
                    endpoints.append(endpoint)
    
    # Output as JSON
    result = {
        'provider_id': provider_id,
        'base_path': base_path,
        'endpoints': endpoints,
        'security_schemes': spec.get('components', {}).get('securitySchemes', {})
    }
    
    print(json.dumps(result, indent=2))
    
except Exception as e:
    print(f"Error parsing OpenAPI spec: {e}", file=sys.stderr)
    sys.exit(1)
EOF
then
    echo "✅ Successfully parsed OpenAPI spec"
    echo "   Endpoints file: $endpoints_file"
    echo "   Size: $(wc -c < "$endpoints_file") bytes"
    
    # Show what endpoints were found
    endpoint_count=$(python3 -c "
import json
with open('$endpoints_file', 'r') as f:
    data = json.load(f)
print(len(data['endpoints']))
" 2>/dev/null)
    echo "   Found: $endpoint_count endpoints"
    
    # Show the endpoints
    echo ""
    echo "📋 Parsed endpoints:"
    python3 -c "
import json
with open('$endpoints_file', 'r') as f:
    data = json.load(f)
for i, ep in enumerate(data['endpoints'], 1):
    print(f'  {i}. {ep[\"method\"]} {ep[\"path\"]} ({ep[\"operationId\"]})')
"
else
    echo "❌ Failed to parse OpenAPI endpoints"
    exit 1
fi

# Test the endpoint processing logic (from setup_macos.sh)
echo ""
echo "🔧 Processing endpoints (setup_macos.sh logic)..."
temp_endpoints="$cache_dir/${provider_id}_temp_endpoints.txt"

python3 -c "
import json
import sys

try:
    with open('$endpoints_file', 'r') as f:
        data = json.load(f)
    # Sort to process AI endpoints first
    endpoints = sorted(data['endpoints'], key=lambda x: not x.get('is_ai_endpoint', False))
    for ep in endpoints:
        print(f\"{ep['path']}|{ep['method']}|{ep['operationId']}|{ep.get('is_ai_endpoint', False)}\")
except Exception as e:
    print(f\"Error processing endpoints: {e}\", file=sys.stderr)
    sys.exit(1)
" > "$temp_endpoints"

if [ -f "$temp_endpoints" ] && [ -s "$temp_endpoints" ]; then
    echo "✅ Successfully processed endpoints"
    echo "   Temp file: $temp_endpoints"
    
    echo ""
    echo "📋 Processed endpoints:"
    cat "$temp_endpoints"
    
    echo ""
    echo "🔧 Would create these routes:"
    processed_count=0
    while IFS='|' read -r path method op_id is_ai; do
        processed_count=$((processed_count + 1))
        
        # Generate route ID (from create_openapi_route function)
        # Use md5 on macOS, md5sum on Linux
        if command -v md5 > /dev/null 2>&1; then
            path_hash=$(echo -n "${method}:${path}" | md5 | cut -c1-8)
        else
            path_hash=$(echo -n "${method}:${path}" | md5sum | cut -c1-8)
        fi
        safe_operation_id=$(echo "$op_id" | sed 's/[^a-zA-Z0-9-]/-/g' | tr '[:upper:]' '[:lower:]')
        route_id="openapi-${provider_id}-${safe_operation_id}-${path_hash}"
        
        # Convert OpenAPI path to APISIX URI
        apisix_path=$(echo "$path" | sed 's/{[^}]*}/*/g')
        uri="/ai/openapi/${provider_id}${apisix_path}"
        
        echo "  $processed_count. Route ID: $route_id"
        echo "      URI: $uri"
        echo "      Target: ${base_url}${path}"
        echo ""
    done < "$temp_endpoints"
    
else
    echo "❌ Failed to process endpoints"
    cat "$temp_endpoints" 2>/dev/null || echo "No temp endpoints file created"
fi

echo ""
echo "🧹 Cleaning up..."
rm -rf "$cache_dir"

echo "✅ Debug test complete"