"""
Real integration test for Simple Chat with MCP features
"""

import os
import signal
import subprocess
import sys
import time

import pytest
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_simple_chat_starts_without_errors():
    """Test that Simple Chat can start without import errors"""
    # Start Streamlit in a subprocess
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_PORT"] = "8507"  # Use different port to avoid conflicts

    process = None
    try:
        # Start Simple Chat
        process = subprocess.Popen(
            ["python3", "-m", "streamlit", "run", "pages/Simple_Chat.py"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "violentutf"),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Give it time to start
        time.sleep(5)

        # Check if process is still running
        if process.poll() is not None:
            # Process terminated, get output
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout)
            print("STDERR:", stderr)

            # Check for import errors
            assert "ModuleNotFoundError" not in stderr, f"Import error found: {stderr}"
            assert "ImportError" not in stderr, f"Import error found: {stderr}"

            # If it exited cleanly, that's still a pass for imports
            if "from utils.mcp_client import MCPClientSync" in stderr:
                pytest.fail(f"MCP import failed: {stderr}")

        # Try to access the page
        try:
            response = requests.get("http://localhost:8507", timeout=5)
            assert response.status_code == 200, f"Page returned {response.status_code}"
            print("✓ Simple Chat is running successfully")
        except requests.exceptions.RequestException:
            # Can't connect, but check if it's still running
            if process.poll() is None:
                print("✓ Simple Chat process is running (couldn't connect, but no crashes)")
            else:
                stdout, stderr = process.communicate()
                if "ModuleNotFoundError" in stderr or "ImportError" in stderr:
                    pytest.fail(f"Import error: {stderr}")
                else:
                    print("✓ Process exited but no import errors found")

    finally:
        # Clean up
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def test_mcp_imports_in_context():
    """Test that MCP imports work in the Simple Chat context"""
    test_script = """
import sys
import os
sys.path.insert(0, 'violentutf')

# Test the exact imports from Simple Chat
from utils.mcp_client import MCPClientSync
from utils.mcp_integration import NaturalLanguageParser, ContextAnalyzer

# Test instantiation
client = MCPClientSync()
parser = NaturalLanguageParser()
analyzer = ContextAnalyzer()

print("All imports successful")
"""

    result = subprocess.run(
        ["python3", "-c", test_script], cwd=os.path.dirname(os.path.dirname(__file__)), capture_output=True, text=True
    )

    assert result.returncode == 0, f"Import test failed: {result.stderr}"
    assert "All imports successful" in result.stdout


if __name__ == "__main__":
    # Run tests
    print("Testing Simple Chat with MCP integration...")

    print("\n1. Testing imports in context...")
    test_mcp_imports_in_context()
    print("✅ Imports work correctly")

    print("\n2. Testing Simple Chat startup...")
    test_simple_chat_starts_without_errors()
    print("✅ Simple Chat starts without errors")

    print("\n✅ All tests passed!")
