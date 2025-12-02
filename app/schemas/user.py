"""
User schemas for request/response validation.
"""

from datetime import datetime
from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    business_name: str | None = Field(None, max_length=255)
    business_address: str | None = None
    business_phone: str | None = Field(None, max_length=50)
    business_email: EmailStr | None = None
    tax_id: str | None = Field(None, max_length=100)
    logo_url: str | None = Field(None, max_length=500)


class UserCreate(BaseSchema):
    """Schema for creating a new user."""
    
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    business_name: str | None = Field(None, max_length=255)
    business_phone: str | None = Field(None, max_length=50)


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""
    
    full_name: str | None = Field(None, min_length=2, max_length=255)
    business_name: str | None = Field(None, max_length=255)
    business_address: str | None = None
    business_phone: str | None = Field(None, max_length=50)
    business_email: EmailStr | None = None
    tax_id: str | None = Field(None, max_length=100)
    logo_url: str | None = Field(None, max_length=500)


class UserResponse(BaseSchema):
    """User response schema (public data)."""
    
    id: int
    email: EmailStr
    full_name: str
    business_name: str | None
    business_address: str | None
    business_phone: str | None
    business_email: str | None
    tax_id: str | None
    logo_url: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserInDB(UserResponse):
    """User schema with hashed password (internal use)."""
    
    hashed_password: str

