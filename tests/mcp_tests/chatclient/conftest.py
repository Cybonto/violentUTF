"""
Local conftest for MCP client tests
"""

import sys
import os

# Add violentutf directory to Python path
violentutf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../violentutf"))
if violentutf_path not in sys.path:
    sys.path.insert(0, violentutf_path)
