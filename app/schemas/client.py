"""
Client schemas for request/response validation.
"""

from datetime import datetime
from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class ClientBase(BaseSchema):
    """Base client schema with common fields."""
    
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str = Field(default="France", max_length=100)
    tax_id: str | None = Field(None, max_length=100)
    notes: str | None = None


class ClientCreate(ClientBase):
    """Schema for creating a new client."""
    pass


class ClientUpdate(BaseSchema):
    """Schema for updating a client."""
    
    name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    tax_id: str | None = Field(None, max_length=100)
    notes: str | None = None


class ClientResponse(ClientBase):
    """Client response schema."""
    
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseSchema):
    """Paginated client list response."""
    
    items: list[ClientResponse]
    total: int
    page: int
    per_page: int
    pages: int

