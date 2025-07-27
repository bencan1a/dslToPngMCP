"""
Authentication Utilities
=======================

Authentication utilities for API endpoints.
Provides API key validation and hashing.
"""

import hashlib
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from src.config.settings import get_settings

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key_hash(api_key: str) -> str:
    """
    Hash API key for storage and comparison.

    Args:
        api_key: API key to hash

    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


async def validate_api_key(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    Validate API key.

    Args:
        api_key: API key from header

    Returns:
        API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    settings = get_settings()

    # Skip validation in development mode if configured
    if settings.debug and settings.skip_api_key_validation:
        return "development_key"

    # Check if API key is provided
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key is required", headers={"WWW-Authenticate": "ApiKey"}
        )

    # Get valid API keys from settings
    valid_api_keys = settings.api_keys

    # Check if API key is valid
    if api_key not in valid_api_keys:
        # Check hashed API keys
        api_key_hash = get_api_key_hash(api_key)
        if api_key_hash not in settings.api_key_hashes:
            raise HTTPException(
                status_code=401, detail="Invalid API key", headers={"WWW-Authenticate": "ApiKey"}
            )

    return api_key
