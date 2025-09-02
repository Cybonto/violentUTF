# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Local conftest for MCP client tests
"""

import os
import sys

# Add violentutf directory to Python path
violentutf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../violentutf"))
if violentutf_path not in sys.path:
    sys.path.insert(0, violentutf_path)
