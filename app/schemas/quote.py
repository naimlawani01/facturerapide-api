"""
Quote schemas for request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from pydantic import Field

from app.schemas.base import BaseSchema
from app.models.quote import QuoteStatus


class QuoteItemBase(BaseSchema):
    """Base quote item schema."""
    
    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit: str = Field(default="unité", max_length=50)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("20.00"), ge=0, le=100)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class QuoteItemCreate(QuoteItemBase):
    """Schema for creating a quote item."""
    
    product_id: int | None = None


class QuoteItemResponse(QuoteItemBase):
    """Quote item response schema."""
    
    id: int
    quote_id: int
    product_id: int | None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime


class QuoteBase(BaseSchema):
    """Base quote schema."""
    
    client_id: int
    issue_date: date
    validity_date: date
    notes: str | None = None
    terms: str | None = None


class QuoteCreate(QuoteBase):
    """Schema for creating a quote."""
    
    items: list[QuoteItemCreate] = Field(default_factory=list)


class QuoteUpdate(BaseSchema):
    """Schema for updating a quote."""
    
    client_id: int | None = None
    issue_date: date | None = None
    validity_date: date | None = None
    notes: str | None = None
    terms: str | None = None
    status: QuoteStatus | None = None


class QuoteResponse(QuoteBase):
    """Quote response schema."""
    
    id: int
    owner_id: int
    quote_number: str
    status: QuoteStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    converted_invoice_id: int | None
    pdf_path: str | None
    is_expired: bool
    can_convert: bool
    items: list[QuoteItemResponse]
    created_at: datetime
    updated_at: datetime


class QuoteListResponse(BaseSchema):
    """Paginated quote list response."""
    
    items: list[QuoteResponse]
    total: int
    page: int
    per_page: int
    pages: int


class QuoteSummary(BaseSchema):
    """Quote summary for list views."""
    
    id: int
    quote_number: str
    client_name: str
    status: QuoteStatus
    issue_date: date
    validity_date: date
    total: Decimal
    is_expired: bool

