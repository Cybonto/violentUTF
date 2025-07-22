#!/usr/bin/env python3
"""
Test blocks registry directly without authentication
"""

import sys
import os

# Add the FastAPI app path
sys.path.append(os.path.join(os.path.dirname(__file__), '../violentutf_api/fastapi_app'))

from app.services.report_system.block_base import block_registry
from app.services.report_system.report_engine import ReportEngine


def test_block_registry():
    """Test the block registry directly"""
    print("🔍 Testing Block Registry...")
    print("=" * 50)
    
    # Export registry
    registry_data = block_registry.export_registry()
    
    print(f"\n📊 Block Registry Contents:")
    print(f"Number of blocks: {len(registry_data['blocks'])}")
    print(f"Categories: {registry_data['categories']}")
    
    print("\n📦 Available Blocks:")
    for block_type, block_info in registry_data['blocks'].items():
        definition = block_info['definition']
        print(f"\n  {definition['display_name']} ({block_type})")
        print(f"  - Category: {definition['category']}")
        print(f"  - Description: {definition['description']}")
        print(f"  - Supported formats: {definition['supported_formats']}")
        print(f"  - Required variables: {definition['required_variables']}")
        
        # Show configuration schema
        if definition['configuration_schema'].get('properties'):
            print(f"  - Configuration options:")
            for prop, schema in definition['configuration_schema']['properties'].items():
                print(f"    • {prop}: {schema.get('description', 'No description')}")


def test_block_creation():
    """Test creating block instances"""
    print("\n\n🏗️  Testing Block Creation...")
    print("=" * 50)
    
    # Try creating an executive summary block
    block_type = "executive_summary"
    
    print(f"\nCreating {block_type} block...")
    
    try:
        block = block_registry.create_block(
            block_type=block_type,
            block_id="test-exec-summary",
            title="Test Executive Summary",
            configuration={
                "components": ["Overall Risk Score", "Critical Vulnerabilities Count"],
                "highlight_threshold": "High and Above",
                "include_charts": True,
                "max_findings": 5
            }
        )
        
        print("✅ Block created successfully!")
        print(f"   Block ID: {block.block_id}")
        print(f"   Title: {block.title}")
        print(f"   Required variables: {block.get_required_variables()}")
        
        # Test validation
        errors = block.validate_configuration()
        if errors:
            print(f"   ⚠️ Validation errors: {errors}")
        else:
            print("   ✅ Configuration is valid")
            
    except Exception as e:
        print(f"❌ Failed to create block: {e}")


def test_report_engine():
    """Test the report engine"""
    print("\n\n🚀 Testing Report Engine...")
    print("=" * 50)
    
    # Create a simple report configuration
    config = {
        "title": "Test Security Report",
        "format": "Markdown",
        "blocks": [
            {
                "block_id": "exec-summary-1",
                "block_type": "executive_summary",
                "title": "Executive Summary",
                "configuration": {
                    "components": ["Overall Risk Score"],
                    "highlight_threshold": "High and Above",
                    "include_charts": False,
                    "max_findings": 3
                }
            }
        ],
        "output_settings": {
            "include_toc": True,
            "include_metadata": True
        }
    }
    
    print("\nCreating report engine...")
    try:
        engine = ReportEngine()
        
        # Validate configuration
        errors = engine.validate_configuration(config)
        if errors:
            print(f"⚠️ Configuration errors: {errors}")
        else:
            print("✅ Configuration is valid")
            
        # Get required variables
        required_vars = engine.get_required_variables(config)
        print(f"\nRequired variables: {required_vars}")
        
    except Exception as e:
        print(f"❌ Failed to create report engine: {e}")


def main():
    """Run all tests"""
    print("🧪 Direct Block Registry Testing")
    print("=" * 50)
    
    test_block_registry()
    test_block_creation()
    test_report_engine()
    
    print("\n\n✅ All direct tests completed!")


if __name__ == "__main__":
    main()