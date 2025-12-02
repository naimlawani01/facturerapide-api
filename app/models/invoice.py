"""
Invoice and InvoiceItem models for billing.
Supports draft, sent, paid, and cancelled statuses.
"""

from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from datetime import date, datetime
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Integer, Numeric, Date, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.client import Client
    from app.models.payment import Payment


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(BaseModel):
    """
    Invoice model.
    
    Attributes:
        owner_id: Foreign key to the business owner
        client_id: Foreign key to the client
        invoice_number: Unique invoice number (auto-generated)
        status: Current invoice status
        issue_date: Date when invoice was created
        due_date: Payment due date
        notes: Additional notes/terms
        subtotal: Total before tax
        tax_total: Total tax amount
        total: Grand total (subtotal + tax)
        amount_paid: Amount already paid
        pdf_path: Path to generated PDF file
    """
    
    __tablename__ = "invoices"
    
    # Relationships
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    # Invoice info
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus),
        default=InvoiceStatus.DRAFT,
        nullable=False,
    )
    
    # Dates
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    # Notes and terms
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    terms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Totals (calculated from items)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )
    
    # PDF storage
    pdf_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Sent tracking
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="invoices",
    )
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="invoices",
    )
    items: Mapped[List["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    @property
    def balance_due(self) -> Decimal:
        """Calculate remaining balance."""
        return self.total - self.amount_paid
    
    @property
    def is_fully_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.amount_paid >= self.total
    
    def calculate_totals(self) -> None:
        """Recalculate invoice totals from items."""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.tax_total = sum(item.tax_amount for item in self.items)
        self.total = self.subtotal + self.tax_total
    
    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number='{self.invoice_number}', total={self.total})>"


class InvoiceItem(BaseModel):
    """
    Invoice line item model.
    
    Attributes:
        invoice_id: Foreign key to the invoice
        product_id: Optional foreign key to a product
        description: Item description
        quantity: Number of units
        unit_price: Price per unit (HT)
        tax_rate: VAT rate for this item
        discount_percent: Discount percentage
    """
    
    __tablename__ = "invoice_items"
    
    # Relationships
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Item info
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        default=Decimal("1.00"),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        default="unité",
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("20.00"),
        nullable=False,
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="items",
    )
    
    @property
    def subtotal(self) -> Decimal:
        """Calculate line subtotal before tax."""
        gross = self.quantity * self.unit_price
        discount = gross * (self.discount_percent / 100)
        return gross - discount
    
    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax amount for this item."""
        return self.subtotal * (self.tax_rate / 100)
    
    @property
    def total(self) -> Decimal:
        """Calculate line total including tax."""
        return self.subtotal + self.tax_amount
    
    def __repr__(self) -> str:
        return f"<InvoiceItem(id={self.id}, description='{self.description[:30]}...', total={self.total})>"

