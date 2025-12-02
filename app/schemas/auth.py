"""
Authentication schemas.
"""

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    """Login request schema."""
    
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseSchema):
    """Registration request schema."""
    
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    business_name: str | None = Field(None, max_length=255)
    business_phone: str | None = Field(None, max_length=50)


class Token(BaseSchema):
    """Single token response."""
    
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseSchema):
    """Access and refresh token pair response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""
    
    refresh_token: str

