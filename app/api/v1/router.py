"""
API v1 router - aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    clients,
    products,
    invoices,
    payments,
    quotes,
    dashboard,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentification"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Utilisateurs"],
)

api_router.include_router(
    clients.router,
    prefix="/clients",
    tags=["Clients"],
)

api_router.include_router(
    products.router,
    prefix="/products",
    tags=["Produits"],
)

api_router.include_router(
    invoices.router,
    prefix="/invoices",
    tags=["Factures"],
)

api_router.include_router(
    quotes.router,
    prefix="/quotes",
    tags=["Devis"],
)

api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Paiements"],
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)
