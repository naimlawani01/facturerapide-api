"""
Pydantic schemas for request/response validation.
"""

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
)
from app.schemas.client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
)
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceItemCreate,
    InvoiceItemResponse,
)
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
)
from app.schemas.auth import (
    Token,
    TokenPair,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Client
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    # Invoice
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceItemCreate",
    "InvoiceItemResponse",
    # Payment
    "PaymentCreate",
    "PaymentResponse",
    # Auth
    "Token",
    "TokenPair",
    "LoginRequest",
    "RegisterRequest",
    "RefreshTokenRequest",
]

