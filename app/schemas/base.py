"""
Base schema configuration and common schemas.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination parameters."""
    
    page: int = 1
    per_page: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""
    
    total: int
    page: int
    per_page: int
    pages: int
    
    @classmethod
    def create(cls, total: int, page: int, per_page: int):
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(total=total, page=page, per_page=per_page, pages=pages)


class MessageResponse(BaseSchema):
    """Simple message response."""
    
    message: str
    success: bool = True

