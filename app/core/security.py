"""
Security utilities for authentication and authorization.
JWT token handling and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[int] = None
    email: Optional[str] = None
    token_type: str = "access"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data to encode
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token.
    
    Args:
        data: Payload data to encode
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_token_pair(user_id: int, email: str) -> TokenPair:
    """
    Create access and refresh token pair.
    
    Args:
        user_id: User ID to encode
        email: User email to encode
        
    Returns:
        TokenPair with access and refresh tokens
    """
    token_data = {"sub": str(user_id), "email": email}
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token
    )


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        token_type = payload.get("type", "access")
        
        if user_id is None:
            return None
            
        return TokenData(
            user_id=int(user_id),
            email=email,
            token_type=token_type
        )
    except JWTError:
        return None


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verify that a token is of the expected type.
    
    Args:
        token: JWT token to verify
        expected_type: Expected token type (access/refresh)
        
    Returns:
        True if token type matches, False otherwise
    """
    token_data = decode_token(token)
    if token_data is None:
        return False
    return token_data.token_type == expected_type

