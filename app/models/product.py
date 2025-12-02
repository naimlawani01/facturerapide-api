"""
Product/Service model for inventory management.
Supports both physical products with stock and services.
"""

from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Integer, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Product(BaseModel):
    """
    Product/Service model.
    
    Attributes:
        owner_id: Foreign key to the business owner
        name: Product/service name
        description: Detailed description
        sku: Stock Keeping Unit (unique identifier)
        unit_price: Price per unit (HT - hors taxe)
        tax_rate: VAT rate (e.g., 20.0 for 20%)
        unit: Unit of measurement (pièce, heure, kg, etc.)
        is_service: Whether this is a service (no stock management)
        stock_quantity: Current stock level (for products only)
        low_stock_threshold: Alert when stock falls below this level
        is_active: Whether the product is available for sale
    """
    
    __tablename__ = "products"
    
    # Owner relationship
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Product info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    sku: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    
    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("20.00"),  # Default French VAT
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        default="unité",
        nullable=False,
    )
    
    # Stock management
    is_service: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="products",
    )
    
    @property
    def is_low_stock(self) -> bool:
        """Check if product is low on stock."""
        if self.is_service:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def price_ttc(self) -> Decimal:
        """Calculate price including tax (TTC)."""
        return self.unit_price * (1 + self.tax_rate / 100)
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.unit_price})>"

