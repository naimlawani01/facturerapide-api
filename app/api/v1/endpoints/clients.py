"""
Client management endpoints.
CRUD operations for clients.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, CurrentUser
from app.schemas.client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse,
)
from app.schemas.base import MessageResponse
from app.services.client import ClientService


router = APIRouter()


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un client",
    description="Créer un nouveau client",
)
async def create_client(
    data: ClientCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClientResponse:
    """Create a new client."""
    service = ClientService(db)
    client = await service.create(current_user, data)
    return ClientResponse.model_validate(client)


@router.get(
    "",
    response_model=ClientListResponse,
    summary="Lister les clients",
    description="Obtenir la liste paginée des clients",
)
async def list_clients(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page"),
    search: str | None = Query(None, description="Rechercher par nom ou email"),
) -> ClientListResponse:
    """List all clients with pagination."""
    service = ClientService(db)
    skip = (page - 1) * per_page
    
    clients, total = await service.list(
        owner_id=current_user.id,
        skip=skip,
        limit=per_page,
        search=search,
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Détails d'un client",
    description="Obtenir les détails d'un client",
)
async def get_client(
    client_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ClientResponse:
    """Get client by ID."""
    service = ClientService(db)
    client = await service.get_or_404(client_id, current_user.id)
    return ClientResponse.model_validate(client)


@router.patch(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Mettre à jour un client",
    description="Mettre à jour les informations d'un client",
)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClientResponse:
    """Update a client."""
    service = ClientService(db)
    client = await service.get_or_404(client_id, current_user.id)
    client = await service.update(client, data)
    return ClientResponse.model_validate(client)


@router.delete(
    "/{client_id}",
    response_model=MessageResponse,
    summary="Supprimer un client",
    description="Supprimer un client (impossible si des factures existent)",
)
async def delete_client(
    client_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Delete a client."""
    service = ClientService(db)
    client = await service.get_or_404(client_id, current_user.id)
    await service.delete(client)
    return MessageResponse(message="Client supprimé avec succès")

