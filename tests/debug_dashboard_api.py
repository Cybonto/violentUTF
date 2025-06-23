#!/usr/bin/env python3
"""
Debug script to trace exactly what the dashboard API calls are doing
and why they can't find scorer execution results.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the violentutf directory to Python path
sys.path.append('/Users/tamnguyen/Documents/GitHub/ViolentUTF_nightly/violentutf')

# Load environment variables
load_dotenv('/Users/tamnguyen/Documents/GitHub/ViolentUTF_nightly/violentutf/.env')

from utils.jwt_manager import jwt_manager
from utils.user_context import get_user_context_for_token
from utils.logging import get_logger

logger = get_logger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:9080"

def get_auth_headers():
    """Get authentication headers exactly like the dashboards do"""
    try:
        # Get consistent user context (same as Configure Scorers)
        user_context = get_user_context_for_token()
        print(f"🔑 User context: {user_context['preferred_username']}")
        
        # Create token with consistent user context
        api_token = jwt_manager.create_token(user_context)
        
        if not api_token:
            print("❌ Failed to create API token")
            return {}
            
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX"
        }
        
        # Add APISIX API key
        apisix_api_key = (
            os.getenv("VIOLENTUTF_API_KEY") or 
            os.getenv("APISIX_API_KEY") or
            os.getenv("AI_GATEWAY_API_KEY")
        )
        if apisix_api_key:
            headers["apikey"] = apisix_api_key
            print(f"🔐 Using APISIX API key: {apisix_api_key[:8]}...")
        
        return headers
    except Exception as e:
        print(f"❌ Error getting auth headers: {e}")
        return {}

def api_request(method, url, **kwargs):
    """Make API request exactly like the dashboards do"""
    headers = get_auth_headers()
    if not headers.get("Authorization"):
        print("❌ No authorization token available")
        return None
    
    try:
        print(f"📡 Making {method} request to {url}")
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Success! Response size: {len(str(data))} chars")
            return data
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request exception: {e}")
        return None

def debug_orchestrator_flow():
    """Debug the exact flow that Dashboard_2 uses"""
    print("\n" + "="*60)
    print("🔍 DEBUGGING DASHBOARD ORCHESTRATOR FLOW")
    print("="*60)
    
    # Step 1: Get all orchestrators (like the fixed dashboards do)
    print("\n1️⃣ Getting all orchestrators...")
    orchestrators_response = api_request("GET", f"{API_BASE_URL}/api/v1/orchestrators")
    
    if not orchestrators_response:
        print("❌ Failed to get orchestrators")
        return
    
    # API returns list directly, not wrapped in 'orchestrators' key
    orchestrators = orchestrators_response if isinstance(orchestrators_response, list) else orchestrators_response.get('orchestrators', [])
    print(f"📊 Found {len(orchestrators)} total orchestrators")
    
    # Filter for scorer-related orchestrators
    scorer_orchestrators = [o for o in orchestrators if 'scorer' in o.get('name', '').lower()]
    print(f"🎯 Found {len(scorer_orchestrators)} scorer-related orchestrators:")
    
    for orch in scorer_orchestrators:
        print(f"   - {orch.get('name', 'Unknown')}")
        print(f"     Available fields: {list(orch.keys())}")
        print(f"     ID field: {orch.get('id', 'MISSING!')}")
        print(f"     UID field: {orch.get('uid', 'MISSING!')}")
        print(f"     _id field: {orch.get('_id', 'MISSING!')}")
        print()
    
    if not scorer_orchestrators:
        print("⚠️  No scorer orchestrators found!")
        return
    
    # Step 2: Get executions for each scorer orchestrator
    print(f"\n2️⃣ Getting executions for {len(scorer_orchestrators)} scorer orchestrators...")
    all_executions = []
    
    for orchestrator in scorer_orchestrators:
        orch_id = orchestrator.get('orchestrator_id')
        orch_name = orchestrator.get('name', 'Unknown')
        
        print(f"\n🔍 Getting executions for: {orch_name}")
        exec_url = f"{API_BASE_URL}/api/v1/orchestrators/{orch_id}/executions"
        exec_response = api_request("GET", exec_url)
        
        if exec_response and 'executions' in exec_response:
            executions = exec_response['executions']
            print(f"📊 Found {len(executions)} executions for this orchestrator")
            
            for execution in executions:
                execution['orchestrator_name'] = orch_name
                execution['orchestrator_type'] = orchestrator.get('type', '')
                all_executions.append(execution)
                
                # Print execution details
                print(f"   - Execution ID: {execution.get('id', 'Unknown')[:8]}...")
                print(f"   - Status: {execution.get('status', 'Unknown')}")
                print(f"   - Created: {execution.get('created_at', 'Unknown')}")
                print(f"   - Has scorer results: {execution.get('has_scorer_results', False)}")
        else:
            print(f"❌ No executions found for {orch_name}")
    
    print(f"\n📊 Total executions found: {len(all_executions)}")
    
    # Skip Steps 3 and go directly to testing completed executions
    print(f"\n🚀 BYPASSING FILTERING - Testing completed executions directly...")
    
    # Find completed executions (regardless of has_scorer_results flag)
    completed_executions = [e for e in all_executions if e.get('status') == 'completed']
    print(f"📊 Found {len(completed_executions)} completed executions")
    
    if not completed_executions:
        print("❌ No completed executions to test!")
        return
    
    # Test the first few completed executions
    for i, execution in enumerate(completed_executions[:3]):
        execution_id = execution.get('id')
        print(f"\n🔍 Testing execution {i+1}: {execution_id}")
        
        results_url = f"{API_BASE_URL}/api/v1/orchestrators/executions/{execution_id}/results"
        results_response = api_request("GET", results_url)
        
        if results_response:
            scores = results_response.get('scores', [])
            print(f"📊 Found {len(scores)} scores in execution results")
            
            if scores:
                print("✅ SUCCESS! Found scorer results that should be visible in dashboard")
                sample_score = scores[0]
                print(f"📝 Sample score:")
                print(f"   - Score value: {sample_score.get('score_value')}")
                print(f"   - Score type: {sample_score.get('score_type')}")
                print(f"   - Score category: {sample_score.get('score_category')}")
                print(f"   - Scorer metadata: {sample_score.get('score_metadata', 'None')[:100]}...")
                
                # Test if this should fix Dashboard_2 filtering
                print(f"\n🎯 DASHBOARD FILTERING TEST:")
                print(f"   - Execution has scorer results flag: {execution.get('has_scorer_results', False)}")
                print(f"   - But actually HAS {len(scores)} scores!")
                print(f"   - Dashboard_2 should now show this data since we commented out the filtering")
                break
            else:
                print("❌ No scores found in this execution")
        else:
            print(f"❌ Failed to get results for execution {execution_id}")
    
    print(f"\n📊 SUMMARY:")
    print(f"   - Total executions: {len(all_executions)}")
    print(f"   - Completed executions: {len(completed_executions)}")
    print(f"   - Executions with has_scorer_results=True: {len([e for e in all_executions if e.get('has_scorer_results', False)])}")
    print(f"   - Since we commented out the filtering in Dashboard_2, it should now show data from completed executions!")

if __name__ == "__main__":
    print("🚀 DASHBOARD API DEBUG SCRIPT")
    print("This script traces exactly what Dashboard_2 does to find scorer executions")
    
    debug_orchestrator_flow()
    
    print("\n" + "="*60)
    print("🎯 NEXT STEPS:")
    print("If this script found scorer executions, but Dashboard_2 still shows none,")
    print("then there's a bug in the dashboard code that this debug revealed.")
    print("="*60)