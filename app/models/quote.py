"""
Quote (Devis) model for creating estimates before invoices.
Can be converted to Invoice when accepted.
"""

from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from datetime import date
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Integer, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.client import Client


class QuoteStatus(str, Enum):
    """Quote status enumeration."""
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"  # Converted to invoice


class Quote(BaseModel):
    """
    Quote (Devis) model.
    
    Attributes:
        owner_id: Foreign key to the business owner
        client_id: Foreign key to the client
        quote_number: Unique quote number (auto-generated)
        status: Current quote status
        issue_date: Date when quote was created
        validity_date: Quote validity expiration date
        notes: Additional notes/terms
        subtotal: Total before tax
        tax_total: Total tax amount
        total: Grand total (subtotal + tax)
        converted_invoice_id: ID of invoice if converted
        pdf_path: Path to generated PDF file
    """
    
    __tablename__ = "quotes"
    
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
    
    # Quote info
    quote_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[QuoteStatus] = mapped_column(
        SQLEnum(QuoteStatus),
        default=QuoteStatus.DRAFT,
        nullable=False,
    )
    
    # Dates
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    validity_date: Mapped[date] = mapped_column(
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
    
    # Conversion tracking
    converted_invoice_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # PDF storage
    pdf_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
    )
    client: Mapped["Client"] = relationship(
        "Client",
        foreign_keys=[client_id],
    )
    items: Mapped[List["QuoteItem"]] = relationship(
        "QuoteItem",
        back_populates="quote",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        return date.today() > self.validity_date and self.status == QuoteStatus.SENT
    
    @property
    def can_convert(self) -> bool:
        """Check if quote can be converted to invoice."""
        return self.status == QuoteStatus.ACCEPTED
    
    def calculate_totals(self) -> None:
        """Recalculate quote totals from items."""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.tax_total = sum(item.tax_amount for item in self.items)
        self.total = self.subtotal + self.tax_total
    
    def __repr__(self) -> str:
        return f"<Quote(id={self.id}, number='{self.quote_number}', total={self.total})>"


class QuoteItem(BaseModel):
    """
    Quote line item model.
    
    Attributes:
        quote_id: Foreign key to the quote
        product_id: Optional foreign key to a product
        description: Item description
        quantity: Number of units
        unit_price: Price per unit (HT)
        tax_rate: VAT rate for this item
        discount_percent: Discount percentage
    """
    
    __tablename__ = "quote_items"
    
    # Relationships
    quote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quotes.id", ondelete="CASCADE"),
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
    quote: Mapped["Quote"] = relationship(
        "Quote",
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
        return f"<QuoteItem(id={self.id}, description='{self.description[:30]}...', total={self.total})>"

