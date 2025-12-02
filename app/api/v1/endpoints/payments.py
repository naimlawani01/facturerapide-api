"""
Payment management endpoints.
Create and list payments.
"""

from datetime import date
from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, CurrentUser
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse,
)
from app.schemas.base import MessageResponse
from app.models.payment import PaymentMethod
from app.services.payment import PaymentService


router = APIRouter()


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer un paiement",
    description="Enregistrer un paiement pour une facture",
)
async def create_payment(
    data: PaymentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PaymentResponse:
    """Create a new payment."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        service = PaymentService(db)
        payment = await service.create(current_user.id, data)
        return PaymentResponse.model_validate(payment)
    except Exception as e:
        logger.error(f"Erreur lors de la création du paiement: {e}", exc_info=True)
        raise


@router.get(
    "",
    response_model=PaymentListResponse,
    summary="Lister les paiements",
    description="Obtenir la liste paginée de tous les paiements",
)
async def list_payments(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page"),
    from_date: date | None = Query(None, description="Date de début"),
    to_date: date | None = Query(None, description="Date de fin"),
    payment_method: PaymentMethod | None = Query(None, description="Filtrer par méthode"),
) -> PaymentListResponse:
    """List all payments with pagination and filters."""
    service = PaymentService(db)
    skip = (page - 1) * per_page
    
    payments, total = await service.list(
        owner_id=current_user.id,
        skip=skip,
        limit=per_page,
        from_date=from_date,
        to_date=to_date,
        payment_method=payment_method,
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/invoice/{invoice_id}",
    response_model=list[PaymentResponse],
    summary="Paiements d'une facture",
    description="Obtenir tous les paiements d'une facture",
)
async def list_invoice_payments(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> list[PaymentResponse]:
    """List all payments for an invoice."""
    service = PaymentService(db)
    payments = await service.list_by_invoice(invoice_id, current_user.id)
    return [PaymentResponse.model_validate(p) for p in payments]


@router.get(
    "/stats",
    summary="Statistiques des paiements",
    description="Obtenir les statistiques des paiements",
)
async def get_payment_stats(
    current_user: CurrentUser,
    db: DbSession,
    from_date: date | None = Query(None, description="Date de début"),
    to_date: date | None = Query(None, description="Date de fin"),
) -> dict:
    """Get payment statistics."""
    service = PaymentService(db)
    return await service.get_stats(current_user.id, from_date, to_date)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Détails d'un paiement",
    description="Obtenir les détails d'un paiement",
)
async def get_payment(
    payment_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> PaymentResponse:
    """Get payment by ID."""
    service = PaymentService(db)
    payment = await service.get_or_404(payment_id, current_user.id)
    return PaymentResponse.model_validate(payment)


@router.delete(
    "/{payment_id}",
    response_model=MessageResponse,
    summary="Supprimer un paiement",
    description="Supprimer un paiement (met à jour le statut de la facture)",
)
async def delete_payment(
    payment_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Delete a payment."""
    service = PaymentService(db)
    payment = await service.get_or_404(payment_id, current_user.id)
    await service.delete(payment)
    return MessageResponse(message="Paiement supprimé avec succès")

