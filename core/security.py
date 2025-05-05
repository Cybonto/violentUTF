# /core/security.py

from typing import Optional
from jose import JWTError, jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel
from .config import settings
import aiohttp
import asyncio
from jose.utils import base64url_decode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from models.user_identity import UserIdentity

# Function to retrieve the public key from Keycloak
async def get_public_key(token: str):
    # Extract the token header to get the 'kid'
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get('kid')

    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")

    # Cache for public keys
    if not hasattr(get_public_key, 'public_keys'):
        get_public_key.public_keys = {}

    if kid not in get_public_key.public_keys:
        # Fetch JWKS (JSON Web Key Set) from Keycloak
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs") as response:
                if response.status != 200:
                    raise Exception("Failed to fetch public keys from Keycloak")
                jwks = await response.json()
                for key in jwks['keys']:
                    get_public_key.public_keys[key['kid']] = key

    public_key_info = get_public_key.public_keys.get(kid)
    if not public_key_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: public key not found")

    # Build the public key
    exponent = int.from_bytes(base64url_decode(public_key_info['e'].encode('utf-8')), 'big')
    modulus = int.from_bytes(base64url_decode(public_key_info['n'].encode('utf-8')), 'big')
    public_numbers = rsa.RSAPublicNumbers(exponent, modulus)
    public_key = public_numbers.public_key(backend=default_backend())
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return public_key_pem, public_key_info['alg']

# Verify the token and extract user information
async def verify_token(token: str):
    try:
        public_key_pem, algorithm = await get_public_key(token)
        # Decode the token
        payload = jwt.decode(
            token,
            public_key_pem,
            algorithms=[algorithm],
            #audience=settings.KEYCLOAK_CLIENT_ID,
            audience="account",
            options={"verify_aud": True}
        )
        # Extract user information
        token_data = UserIdentity(
            sub=payload.get("sub"),
            preferred_username=payload.get("preferred_username"),
            email=payload.get("email"),
            roles=payload.get("realm_access", {}).get("roles", [])
        )
        return token_data
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        ) from e

# Dependency function
async def get_current_user(request: Request):
    authorization: str = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")
    token = authorization[len("Bearer "):]
    return await verify_token(token)