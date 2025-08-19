#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
ViolentUTF JWT CLI Tool - Command line interface for JWT key management.

Requirements:
    pip install click requests
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import requests

# Configuration
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:8000")
CONFIG_DIR = Path.home() / ".violentutf"

# Security: HTTP timeout configuration to prevent DoS via hanging connections
DEFAULT_TIMEOUT = 30  # seconds
AUTH_TIMEOUT = 10  # shorter for auth operations
TOKEN_FILE = CONFIG_DIR / "token.json"


def ensure_config_dir() -> None:
    """Ensure configuration directory exists."""
    CONFIG_DIR.mkdir(exist_ok=True)


def save_token(token_data: dict) -> None:
    """Save token to local file."""
    ensure_config_dir()
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)  # Restrict permissions


def load_token() -> Optional[dict]:
    """Load token from local file."""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None


def get_auth_header() -> dict:
    """Get authorization header from saved token."""
    token_data = load_token()
    if not token_data:
        click.echo("No authentication token found. Please login first.", err=True)
        sys.exit(1)
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@click.group()
def cli() -> None:
    """ViolentUTF JWT CLI - Manage JWT tokens for API access."""
    pass


@cli.command()
@click.option("--username", "-u", prompt=True, help="Username")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Password")
def login(username: str, password: str) -> None:
    """Login to ViolentUTF and obtain JWT token."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/token",
            data={"username": username, "password": password, "grant_type": "password"},
            timeout=30,
        )

        if response.status_code == 200:
            token_data = response.json()
            token_data["username"] = username
            token_data["obtained_at"] = datetime.utcnow().isoformat()
            save_token(token_data)
            click.echo(f"Successfully logged in as {username}")
            click.echo(f"Token saved to {TOKEN_FILE}")
        else:
            click.echo(f"Login failed: {response.json().get('detail', 'Unknown error')}", err=True)
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        click.echo(f"Cannot connect to API at {API_BASE_URL}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def logout() -> None:
    """Logout and remove stored token."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        click.echo("Successfully logged out")
    else:
        click.echo("No active session found")


@cli.command()
def whoami() -> None:
    """Show current user information."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/auth/me", headers=get_auth_header(), timeout=30)

        if response.status_code == 200:
            user_info = response.json()
            click.echo(f"Username: {user_info['username']}")
            click.echo(f"Email: {user_info.get('email', 'N/A')}")
            click.echo(f"Roles: {', '.join(user_info.get('roles', []))}")
        else:
            click.echo(f"Error: {response.json().get('detail', 'Unknown error')}", err=True)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def get_token() -> None:
    """Display current JWT token."""
    token_data = load_token()
    if token_data:
        click.echo(f"Token: {token_data['access_token']}")
        click.echo(f"Type: {token_data.get('token_type', 'bearer')}")
        click.echo(f"Username: {token_data.get('username', 'Unknown')}")
        click.echo(f"Obtained: {token_data.get('obtained_at', 'Unknown')}")

        # Check expiration
        if "expires_in" in token_data and "obtained_at" in token_data:
            from datetime import datetime, timedelta

            obtained = datetime.fromisoformat(token_data["obtained_at"])
            expires = obtained + timedelta(seconds=token_data["expires_in"])
            now = datetime.utcnow()

            if now < expires:
                remaining = expires - now
                click.echo(f"Expires in: {remaining}")
            else:
                click.echo("Status: EXPIRED", err=True)
    else:
        click.echo("No token found. Please login first.", err=True)


@cli.command()
def refresh() -> None:
    """Refresh the current token."""
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/auth/refresh", headers=get_auth_header(), timeout=AUTH_TIMEOUT)

        if response.status_code == 200:
            token_data = response.json()
            old_data = load_token()
            token_data["username"] = old_data.get("username", "Unknown")
            token_data["obtained_at"] = datetime.utcnow().isoformat()
            save_token(token_data)
            click.echo("Token refreshed successfully")
        else:
            click.echo(f"Refresh failed: {response.json().get('detail', 'Unknown error')}", err=True)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def keys() -> None:
    """Manage API keys."""
    pass


@keys.command("create")
@click.option("--name", "-n", prompt=True, help="Name for the API key")
@click.option("--permissions", "-p", multiple=True, default=["api:access"], help="Permissions for the key")
def create_key(name: str, permissions: tuple) -> None:
    """Create a new API key."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/keys/create",
            headers=get_auth_header(),
            json={"name": name, "permissions": list(permissions)},
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code == 200:
            key_data = response.json()
            click.echo("API Key created successfully!")
            click.echo(f"Key ID: {key_data['key_id']}")
            click.echo(f"API Key: {key_data['api_key']}")
            click.echo(f"Name: {key_data['name']}")
            click.echo(f"Expires: {key_data['expires_at']}")
            click.echo("\n⚠️  Save this API key securely. You won't be able to see it again!")
        else:
            click.echo(f"Error: {response.json().get('detail', 'Unknown error')}", err=True)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@keys.command("list")
def list_keys() -> None:
    """List all API keys."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/keys/list", headers=get_auth_header(), timeout=DEFAULT_TIMEOUT)

        if response.status_code == 200:
            keys_data = response.json()
            keys = keys_data.get("keys", [])

            if not keys:
                click.echo("No API keys found")
                return

            click.echo(f"Found {len(keys)} API key(s):\n")
            for key in keys:
                click.echo(f"ID: {key['id']}")
                click.echo(f"Name: {key['name']}")
                click.echo(f"Created: {key['created_at']}")
                click.echo(f"Expires: {key['expires_at']}")
                click.echo(f"Active: {'Yes' if key['active'] else 'No'}")
                click.echo(f"Permissions: {', '.join(key['permissions'])}")
                click.echo("")
        else:
            click.echo(f"Error: {response.json().get('detail', 'Unknown error')}", err=True)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@keys.command("revoke")
@click.argument("key_id")
def revoke_key(key_id: str) -> None:
    """Revoke an API key."""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/keys/{key_id}", headers=get_auth_header(), timeout=DEFAULT_TIMEOUT
        )

        if response.status_code == 200:
            click.echo(f"API key {key_id} revoked successfully")
        else:
            click.echo(f"Error: {response.json().get('detail', 'Unknown error')}", err=True)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@keys.command("current")
def get_current_key() -> None:
    """Get current session as API key format."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/keys/current", headers=get_auth_header(), timeout=DEFAULT_TIMEOUT
        )

        if response.status_code == 200:
            key_data = response.json()
            click.echo("Session API Key:")
            click.echo(f"API Key: {key_data['api_key']}")
            click.echo(f"Expires: {key_data['expires_at']}")
            click.echo(f"Permissions: {', '.join(key_data['permissions'])}")
        else:
            click.echo(f"Error: {response.json().get('detail', 'Unknown error')}", err=True)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
