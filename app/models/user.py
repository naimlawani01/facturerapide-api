"""
User model for authentication and business ownership.
Each user represents a business owner (artisan, PME).
"""

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.product import Product
    from app.models.invoice import Invoice


class User(BaseModel):
    """
    User model representing a business owner.
    
    Attributes:
        email: Unique email for authentication
        hashed_password: Bcrypt hashed password
        full_name: Business owner's full name
        business_name: Name of the business/company
        business_address: Physical address of the business
        business_phone: Contact phone number
        business_email: Business contact email (can differ from auth email)
        tax_id: Tax identification number (SIRET, NIF, etc.)
        logo_url: URL to business logo for invoices
        is_active: Whether the account is active
        is_verified: Whether email has been verified
    """
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Personal info
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Business info
    business_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    business_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    business_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    business_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    clients: Mapped[List["Client"]] = relationship(
        "Client",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', business='{self.business_name}')>"

