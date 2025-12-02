"""
Invoice schemas for request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.client import ClientResponse
from app.models.invoice import InvoiceStatus


class InvoiceItemBase(BaseSchema):
    """Base invoice item schema."""
    
    description: str = Field(..., min_length=1)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit: str = Field(default="unité", max_length=50)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("20.00"), ge=0, le=100)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating an invoice item."""
    
    product_id: int | None = None


class InvoiceItemUpdate(BaseSchema):
    """Schema for updating an invoice item."""
    
    description: str | None = Field(None, min_length=1)
    quantity: Decimal | None = Field(None, gt=0)
    unit: str | None = Field(None, max_length=50)
    unit_price: Decimal | None = Field(None, ge=0)
    tax_rate: Decimal | None = Field(None, ge=0, le=100)
    discount_percent: Decimal | None = Field(None, ge=0, le=100)


class InvoiceItemResponse(InvoiceItemBase):
    """Invoice item response schema."""
    
    id: int
    invoice_id: int
    product_id: int | None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime


class InvoiceBase(BaseSchema):
    """Base invoice schema."""
    
    client_id: int
    issue_date: date
    due_date: date
    notes: str | None = None
    terms: str | None = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice."""
    
    items: list[InvoiceItemCreate] = Field(default_factory=list)


class InvoiceUpdate(BaseSchema):
    """Schema for updating an invoice."""
    
    client_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    terms: str | None = None
    status: InvoiceStatus | None = None


class InvoiceResponse(InvoiceBase):
    """Invoice response schema."""
    
    id: int
    owner_id: int
    invoice_number: str
    status: InvoiceStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    pdf_path: str | None
    sent_at: datetime | None
    items: list[InvoiceItemResponse]
    client: Optional[ClientResponse] = None  # Include client info
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseSchema):
    """Paginated invoice list response."""
    
    items: list[InvoiceResponse]
    total: int
    page: int
    per_page: int
    pages: int


class InvoiceSummary(BaseSchema):
    """Invoice summary for list views."""
    
    id: int
    invoice_number: str
    client_name: str
    status: InvoiceStatus
    issue_date: date
    due_date: date
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal

