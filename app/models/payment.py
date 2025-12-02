"""
Payment model for tracking invoice payments.
Supports multiple payment methods and partial payments.
"""

from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from datetime import date
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Integer, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.invoice import Invoice


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class Payment(BaseModel):
    """
    Payment model.
    
    Attributes:
        invoice_id: Foreign key to the invoice
        amount: Payment amount
        payment_date: Date of payment
        payment_method: Method of payment
        reference: Payment reference (check number, transaction ID, etc.)
        notes: Additional notes about the payment
    """
    
    __tablename__ = "payments"
    
    # Relationships
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Payment info
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod),
        default=PaymentMethod.CASH,
        nullable=False,
    )
    reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="payments",
    )
    
    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, method='{self.payment_method}')>"

