"""Lightweight authentication for PlantaOS MVP.

Uses SHA-256 hashing (demo only) and Pydantic models. Includes
password reset with in-memory token store.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    """User role levels."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(BaseModel):
    """Authenticated user model."""

    username: str
    password_hash: str
    role: UserRole
    display_name: str


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 (demo only).

    Args:
        password: Plain-text password string.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(password.encode()).hexdigest()


DEFAULT_USERS: list[User] = [
    User(
        username="admin",
        password_hash=_hash_password("admin"),
        role=UserRole.ADMIN,
        display_name="Administrator",
    ),
    User(
        username="operator",
        password_hash=_hash_password("operator"),
        role=UserRole.OPERATOR,
        display_name="Operator",
    ),
    User(
        username="viewer",
        password_hash=_hash_password("viewer"),
        role=UserRole.VIEWER,
        display_name="Viewer",
    ),
]

_ROLE_ORDER = {
    UserRole.VIEWER: 0,
    UserRole.OPERATOR: 1,
    UserRole.ADMIN: 2,
}

_RESET_TOKENS: dict[str, tuple[str, datetime]] = {}


def authenticate(
    username: str,
    password: str,
) -> User | None:
    """Verify credentials against the default user list.

    Args:
        username: Login username.
        password: Plain-text password to verify.

    Returns:
        Matching User model or None if credentials are invalid.
    """
    pw_hash = _hash_password(password)
    for user in DEFAULT_USERS:
        if user.username == username and user.password_hash == pw_hash:
            return user
    return None


def check_role(
    auth_data: dict | None,
    required: UserRole,
) -> bool:
    """Check whether a user meets a minimum role requirement.

    Args:
        auth_data: Dict with at least a 'role' key from session.
        required: Minimum UserRole needed.

    Returns:
        True if role level is sufficient.
    """
    if not auth_data:
        return False
    return _ROLE_ORDER.get(auth_data.get("role", ""), -1) >= _ROLE_ORDER[required]


def create_reset_token(username: str) -> str | None:
    """Generate a password-reset token valid for 30 minutes.

    Args:
        username: Target username for password reset.

    Returns:
        URL-safe token string or None if user not found.
    """
    for user in DEFAULT_USERS:
        if user.username == username:
            token = secrets.token_urlsafe(32)
            _RESET_TOKENS[token] = (
                username,
                datetime.now() + timedelta(minutes=30),
            )
            return token
    return None


def validate_reset_token(
    token: str,
    new_password: str,
) -> bool:
    """Consume a reset token and update the user password.

    Args:
        token: The reset token to validate.
        new_password: New plain-text password to set.

    Returns:
        True if token was valid and password was updated.
    """
    if token not in _RESET_TOKENS:
        return False
    username, expires = _RESET_TOKENS[token]
    if datetime.now() > expires:
        del _RESET_TOKENS[token]
        return False
    new_hash = _hash_password(new_password)
    for user in DEFAULT_USERS:
        if user.username == username:
            user.password_hash = new_hash
            break
    del _RESET_TOKENS[token]
    return True
