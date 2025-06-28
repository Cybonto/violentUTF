"""
User Factory for creating test user instances

This module provides factory functions for creating user test data
including authentication tokens and permissions.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import factory
import jwt
from factory import Faker, LazyAttribute, LazyFunction


class UserFactory(factory.Factory):
    """Factory for creating test users"""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    name = factory.Faker("name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    # Authentication fields
    is_active = True
    is_verified = True
    created_at = factory.Faker("date_time")
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    last_login = factory.LazyAttribute(
        lambda obj: obj.created_at
        + timedelta(days=factory.Faker("pyint", min_value=1, max_value=30).generate())
    )

    # Roles and permissions
    roles = factory.List(["user"])
    permissions = factory.LazyAttribute(
        lambda obj: {
            "user": ["read:generators", "read:datasets", "execute:tests"],
            "admin": ["read:all", "write:all", "delete:all"],
            "developer": [
                "read:all",
                "write:generators",
                "write:datasets",
                "execute:all",
            ],
        }.get(obj.roles[0] if obj.roles else "user", [])
    )

    # Additional metadata
    organization = factory.Faker("company")
    department = factory.Faker("job")

    @factory.lazy_attribute
    def preferred_username(self):
        """Generate preferred username from username"""
        return self.username.lower()


class AdminUserFactory(UserFactory):
    """Factory for creating admin users"""

    username = factory.Sequence(lambda n: f"admin{n}")
    roles = ["admin", "user"]
    is_superuser = True


class DeveloperUserFactory(UserFactory):
    """Factory for creating developer users"""

    username = factory.Sequence(lambda n: f"developer{n}")
    roles = ["developer", "user"]
    department = "Engineering"


class APIUserFactory(UserFactory):
    """Factory for API-only users"""

    username = factory.Sequence(lambda n: f"api_user{n}")
    roles = ["api_user"]
    is_api_user = True
    api_key = factory.LazyFunction(
        lambda: f"vutf_{''.join(factory.Faker('lexify', text='????????').generate() for _ in range(4))}"
    )


class JWTTokenFactory(factory.Factory):
    """Factory for creating JWT tokens"""

    class Meta:
        model = dict

    sub = factory.LazyAttribute(
        lambda obj: obj.user.get("id") if hasattr(obj, "user") else str(uuid.uuid4())
    )
    email = factory.LazyAttribute(
        lambda obj: (
            obj.user.get("email") if hasattr(obj, "user") else Faker("email").generate()
        )
    )
    name = factory.LazyAttribute(
        lambda obj: (
            obj.user.get("name") if hasattr(obj, "user") else Faker("name").generate()
        )
    )
    preferred_username = factory.LazyAttribute(
        lambda obj: (
            obj.user.get("preferred_username")
            if hasattr(obj, "user")
            else Faker("user_name").generate()
        )
    )

    # Token metadata
    iat = factory.LazyFunction(lambda: int(datetime.utcnow().timestamp()))
    exp = factory.LazyAttribute(lambda obj: obj.iat + 3600)  # 1 hour expiry
    iss = "http://localhost:8080/realms/violentutf"
    aud = "violentutf-client"

    # Roles and permissions
    roles = factory.LazyAttribute(
        lambda obj: (
            obj.user.get("roles", ["user"]) if hasattr(obj, "user") else ["user"]
        )
    )
    realm_access = factory.LazyAttribute(lambda obj: {"roles": obj.roles})

    @factory.post_generation
    def encode_token(obj, create, extracted, **kwargs):
        """Encode the JWT token if requested"""
        if extracted:
            secret = kwargs.get("secret", "test-secret-key")
            algorithm = kwargs.get("algorithm", "HS256")

            # Create token payload
            payload = {k: v for k, v in obj.items() if not k.startswith("_")}

            # Encode token
            token = jwt.encode(payload, secret, algorithm=algorithm)
            obj["encoded"] = token
            return token


class KeycloakTokenFactory(factory.Factory):
    """Factory for creating Keycloak-style tokens"""

    class Meta:
        model = dict

    access_token = factory.Faker("sha256")
    refresh_token = factory.Faker("sha256")
    id_token = factory.Faker("sha256")
    token_type = "Bearer"
    expires_in = 3600
    refresh_expires_in = 7200
    scope = "openid email profile"
    session_state = factory.LazyFunction(lambda: str(uuid.uuid4()))

    @factory.lazy_attribute
    def not_before_policy(self):
        """Generate not-before policy timestamp"""
        return 0


def create_test_user(**kwargs) -> Dict[str, Any]:
    """
    Create a test user with optional overrides

    Args:
        **kwargs: Override any user attributes

    Returns:
        Dict containing user data
    """
    return UserFactory(**kwargs)


def create_admin_user(**kwargs) -> Dict[str, Any]:
    """Create an admin user for testing"""
    return AdminUserFactory(**kwargs)


def create_developer_user(**kwargs) -> Dict[str, Any]:
    """Create a developer user for testing"""
    return DeveloperUserFactory(**kwargs)


def create_api_user(**kwargs) -> Dict[str, Any]:
    """Create an API user for testing"""
    return APIUserFactory(**kwargs)


def create_jwt_token(user: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """
    Create a JWT token for testing

    Args:
        user: Optional user dict to base token on
        **kwargs: Override token attributes

    Returns:
        Encoded JWT token string
    """
    factory_kwargs = {}
    if user:
        factory_kwargs["user"] = user
    factory_kwargs.update(kwargs)

    # Create token with encoding
    token_data = JWTTokenFactory(**factory_kwargs, encode_token=True)
    return token_data.get("encoded", "")


def create_expired_token(user: Optional[Dict[str, Any]] = None) -> str:
    """Create an expired JWT token for testing"""
    return create_jwt_token(
        user=user,
        iat=int((datetime.utcnow() - timedelta(hours=2)).timestamp()),
        exp=int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
    )


def create_keycloak_token_response(
    user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a Keycloak token response for testing

    Args:
        user: Optional user to base tokens on

    Returns:
        Dict containing Keycloak token response
    """
    keycloak_token = KeycloakTokenFactory()

    if user:
        # Create proper JWT for id_token
        id_token_payload = JWTTokenFactory(user=user)
        keycloak_token["id_token"] = create_jwt_token(user)

        # Add decoded user info
        keycloak_token["decoded_id_token"] = {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "preferred_username": user["preferred_username"],
            "roles": user.get("roles", ["user"]),
        }

    return keycloak_token


def create_user_batch(count: int = 5, **kwargs) -> List[Dict[str, Any]]:
    """
    Create multiple test users

    Args:
        count: Number of users to create
        **kwargs: Override attributes for all users

    Returns:
        List of user dictionaries
    """
    return UserFactory.create_batch(count, **kwargs)


def create_diverse_users() -> List[Dict[str, Any]]:
    """Create a diverse set of users for comprehensive testing"""
    return [
        create_test_user(username="john_doe", name="John Doe"),
        create_admin_user(username="admin", name="Admin User"),
        create_developer_user(username="dev1", name="Developer One"),
        create_api_user(username="api_client", name="API Client"),
        create_test_user(username="inactive", is_active=False),
        create_test_user(username="unverified", is_verified=False),
    ]


def create_authenticated_request_headers(
    user: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Create authenticated request headers for testing

    Args:
        user: Optional user to create token for

    Returns:
        Dict with Authorization header
    """
    token = create_jwt_token(user or create_test_user())
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
