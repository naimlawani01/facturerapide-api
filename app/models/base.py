"""
Base model with common fields and utilities.
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """
    Abstract base model with ID and timestamps.
    All models should inherit from this.
    """
    
    __abstract__ = True
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

