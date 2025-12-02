"""
Payment schemas for request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from pydantic import Field

from app.schemas.base import BaseSchema
from app.models.payment import PaymentMethod


class PaymentBase(BaseSchema):
    """Base payment schema."""
    
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_method: PaymentMethod = PaymentMethod.CASH
    reference: str | None = Field(None, max_length=100)
    notes: str | None = None


class PaymentCreate(PaymentBase):
    """Schema for creating a payment."""
    
    invoice_id: int


class PaymentResponse(PaymentBase):
    """Payment response schema."""
    
    id: int
    invoice_id: int
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseSchema):
    """Paginated payment list response."""
    
    items: list[PaymentResponse]
    total: int
    page: int
    per_page: int
    pages: int

