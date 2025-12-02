"""
Product management endpoints.
CRUD operations for products and stock management.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, CurrentUser
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    StockUpdateRequest,
)
from app.schemas.base import MessageResponse
from app.services.product import ProductService


router = APIRouter()


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un produit",
    description="Créer un nouveau produit ou service",
)
async def create_product(
    data: ProductCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProductResponse:
    """Create a new product."""
    service = ProductService(db)
    product = await service.create(current_user, data)
    return ProductResponse.model_validate(product)


@router.get(
    "",
    response_model=ProductListResponse,
    summary="Lister les produits",
    description="Obtenir la liste paginée des produits",
)
async def list_products(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page"),
    search: str | None = Query(None, description="Rechercher par nom ou SKU"),
    is_service: bool | None = Query(None, description="Filtrer par type (service ou produit)"),
    is_active: bool | None = Query(None, description="Filtrer par statut actif"),
    low_stock: bool = Query(False, description="Afficher uniquement les produits en rupture"),
) -> ProductListResponse:
    """List all products with pagination and filters."""
    service = ProductService(db)
    skip = (page - 1) * per_page
    
    products, total = await service.list(
        owner_id=current_user.id,
        skip=skip,
        limit=per_page,
        search=search,
        is_service=is_service,
        is_active=is_active,
        low_stock_only=low_stock,
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Détails d'un produit",
    description="Obtenir les détails d'un produit",
)
async def get_product(
    product_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ProductResponse:
    """Get product by ID."""
    service = ProductService(db)
    product = await service.get_or_404(product_id, current_user.id)
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Mettre à jour un produit",
    description="Mettre à jour les informations d'un produit",
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProductResponse:
    """Update a product."""
    service = ProductService(db)
    product = await service.get_or_404(product_id, current_user.id)
    product = await service.update(product, data)
    return ProductResponse.model_validate(product)


@router.post(
    "/{product_id}/stock",
    response_model=ProductResponse,
    summary="Ajuster le stock",
    description="Ajouter ou retirer du stock (quantité positive pour ajouter, négative pour retirer)",
)
async def update_stock(
    product_id: int,
    data: StockUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProductResponse:
    """Update product stock quantity."""
    service = ProductService(db)
    product = await service.get_or_404(product_id, current_user.id)
    product = await service.update_stock(product, data.quantity, data.reason)
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Désactiver un produit",
    description="Désactiver un produit (soft delete)",
)
async def delete_product(
    product_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Delete (deactivate) a product."""
    service = ProductService(db)
    product = await service.get_or_404(product_id, current_user.id)
    await service.delete(product)
    return MessageResponse(message="Produit désactivé avec succès")

