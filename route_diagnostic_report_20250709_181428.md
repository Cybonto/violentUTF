# ViolentUTF Route Diagnostic Report
Generated: Wed Jul  9 18:14:28 EDT 2025

## Summary
- Expected Routes: 1
- Discovered Routes: 1
- Failed Routes: 1

## Expected Routes
- 0: GET:/openapi/gsai-api-1/api/v1/models

## Discovered Routes
- 0:

## Failed Routes
- 0:

## Route Coverage Analysis
[0;34m📊 Analyzing route coverage...[0m
[0;36m🔍 Expected vs Discovered Routes:[0m
   ❌ 0: /openapi/gsai-api-1/api/v1/models (MISSING)

[0;36m📈 Coverage Analysis:[0m
   • Expected routes: 1
   • Found routes: 0
   • Missing routes: 1
   • Coverage rate: 0%
[0;31m❌ Poor route coverage, many routes missing[0m

## Recommendations
- Investigate failed routes and check upstream services
- Verify AI provider configurations and API keys
- Check APISIX logs for detailed error information
