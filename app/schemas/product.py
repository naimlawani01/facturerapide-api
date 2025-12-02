"""
Product schemas for request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import Field

from app.schemas.base import BaseSchema


class ProductBase(BaseSchema):
    """Base product schema with common fields."""
    
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    sku: str | None = Field(None, max_length=100)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("20.00"), ge=0, le=100, decimal_places=2)
    unit: str = Field(default="unité", max_length=50)
    is_service: bool = False
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseSchema):
    """Schema for updating a product."""
    
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    sku: str | None = Field(None, max_length=100)
    unit_price: Decimal | None = Field(None, ge=0, decimal_places=2)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, decimal_places=2)
    unit: str | None = Field(None, max_length=50)
    is_service: bool | None = None
    stock_quantity: int | None = Field(None, ge=0)
    low_stock_threshold: int | None = Field(None, ge=0)
    is_active: bool | None = None


class ProductResponse(ProductBase):
    """Product response schema."""
    
    id: int
    owner_id: int
    is_active: bool
    is_low_stock: bool
    price_ttc: Decimal
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseSchema):
    """Paginated product list response."""
    
    items: list[ProductResponse]
    total: int
    page: int
    per_page: int
    pages: int


class StockUpdateRequest(BaseSchema):
    """Schema for updating product stock."""
    
    quantity: int = Field(..., description="Quantity to add (positive) or remove (negative)")
    reason: str | None = Field(None, max_length=255, description="Reason for stock adjustment")

