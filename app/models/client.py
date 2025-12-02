"""
Client model for managing customers.
Each client belongs to a user (business owner).
"""

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.invoice import Invoice


class Client(BaseModel):
    """
    Client model representing a customer.
    
    Attributes:
        owner_id: Foreign key to the business owner
        name: Client's full name or company name
        email: Client's email address
        phone: Client's phone number
        address: Client's physical address
        tax_id: Client's tax identification number
        notes: Additional notes about the client
    """
    
    __tablename__ = "clients"
    
    # Owner relationship
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Client info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        default="France",
        nullable=False,
    )
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="clients",
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"

