"""
Quote (Devis) management endpoints.
CRUD operations for quotes and conversion to invoice.
"""

from fastapi import APIRouter, Query, status
from fastapi.responses import FileResponse

from app.api.deps import DbSession, CurrentUser
from app.schemas.quote import (
    QuoteCreate,
    QuoteUpdate,
    QuoteResponse,
    QuoteListResponse,
    QuoteItemCreate,
)
from app.schemas.invoice import InvoiceResponse
from app.schemas.base import MessageResponse
from app.models.quote import QuoteStatus
from app.services.quote import QuoteService
from app.services.pdf import PDFService


router = APIRouter()


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un devis",
    description="Créer un nouveau devis avec ses lignes",
)
async def create_quote(
    data: QuoteCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Créer un nouveau devis."""
    service = QuoteService(db)
    quote = await service.create(current_user, data)
    return QuoteResponse.model_validate(quote)


@router.get(
    "",
    response_model=QuoteListResponse,
    summary="Lister les devis",
    description="Obtenir la liste paginée des devis",
)
async def list_quotes(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page"),
    status: QuoteStatus | None = Query(None, description="Filtrer par statut"),
    client_id: int | None = Query(None, description="Filtrer par client"),
) -> QuoteListResponse:
    """Lister tous les devis avec pagination."""
    service = QuoteService(db)
    skip = (page - 1) * per_page
    
    quotes, total = await service.list(
        owner_id=current_user.id,
        skip=skip,
        limit=per_page,
        status=status,
        client_id=client_id,
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return QuoteListResponse(
        items=[QuoteResponse.model_validate(q) for q in quotes],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/stats",
    summary="Statistiques des devis",
    description="Obtenir les statistiques des devis",
)
async def get_quote_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Obtenir les statistiques des devis."""
    service = QuoteService(db)
    return await service.get_stats(current_user.id)


@router.get(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Détails d'un devis",
    description="Obtenir les détails d'un devis",
)
async def get_quote(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Obtenir un devis par ID."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    return QuoteResponse.model_validate(quote)


@router.patch(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Mettre à jour un devis",
    description="Mettre à jour les informations d'un devis",
)
async def update_quote(
    quote_id: int,
    data: QuoteUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Mettre à jour un devis."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    quote = await service.update(quote, data)
    return QuoteResponse.model_validate(quote)


@router.post(
    "/{quote_id}/items",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une ligne",
    description="Ajouter une ligne à un devis",
)
async def add_quote_item(
    quote_id: int,
    data: QuoteItemCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Ajouter une ligne au devis."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    quote = await service.add_item(quote, data, current_user.id)
    return QuoteResponse.model_validate(quote)


@router.delete(
    "/{quote_id}/items/{item_id}",
    response_model=QuoteResponse,
    summary="Supprimer une ligne",
    description="Supprimer une ligne d'un devis",
)
async def remove_quote_item(
    quote_id: int,
    item_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Supprimer une ligne du devis."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    quote = await service.remove_item(quote, item_id)
    return QuoteResponse.model_validate(quote)


@router.post(
    "/{quote_id}/send",
    response_model=QuoteResponse,
    summary="Envoyer le devis",
    description="Marquer le devis comme envoyé",
)
async def send_quote(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Marquer le devis comme envoyé."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    quote = await service.send(quote)
    return QuoteResponse.model_validate(quote)


@router.post(
    "/{quote_id}/accept",
    response_model=QuoteResponse,
    summary="Accepter le devis",
    description="Marquer le devis comme accepté par le client",
)
async def accept_quote(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Accepter le devis."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    quote = await service.accept(quote)
    return QuoteResponse.model_validate(quote)


@router.post(
    "/{quote_id}/reject",
    response_model=QuoteResponse,
    summary="Refuser le devis",
    description="Marquer le devis comme refusé par le client",
)
async def reject_quote(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> QuoteResponse:
    """Refuser le devis."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    quote = await service.reject(quote)
    return QuoteResponse.model_validate(quote)


@router.post(
    "/{quote_id}/convert",
    response_model=InvoiceResponse,
    summary="Convertir en facture",
    description="Convertir un devis accepté en facture",
)
async def convert_to_invoice(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Convertir le devis en facture."""
    service = QuoteService(db)
    quote = await service.get_or_404(quote_id, current_user.id)
    invoice = await service.convert_to_invoice(quote, current_user)
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/{quote_id}/pdf",
    summary="Télécharger le PDF",
    description="Générer et télécharger le devis en PDF",
    response_class=FileResponse,
)
async def download_quote_pdf(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Générer et télécharger le PDF du devis."""
    quote_service = QuoteService(db)
    quote = await quote_service.get_or_404(quote_id, current_user.id)
    
    pdf_service = PDFService()
    pdf_path = await pdf_service.generate_quote_pdf(quote, current_user)
    
    quote.pdf_path = pdf_path
    await db.flush()
    
    return FileResponse(
        path=pdf_path,
        filename=f"devis_{quote.quote_number}.pdf",
        media_type="application/pdf",
    )


@router.post(
    "/{quote_id}/send-email",
    summary="Envoyer par email",
    description="Envoyer le devis par email au client",
)
async def send_quote_email(
    quote_id: int,
    current_user: CurrentUser,
    db: DbSession,
    message: str | None = None,
):
    """Envoyer le devis par email."""
    from app.services.email import EmailService
    
    quote_service = QuoteService(db)
    quote = await quote_service.get_or_404(quote_id, current_user.id)
    
    # Generate PDF first
    pdf_service = PDFService()
    pdf_path = await pdf_service.generate_quote_pdf(quote, current_user)
    quote.pdf_path = pdf_path
    
    # Send email
    email_service = EmailService()
    success = await email_service.send_quote(
        quote=quote,
        owner=current_user,
        client=quote.client,
        pdf_path=pdf_path,
        custom_message=message,
    )
    
    if success:
        # Mark as sent if still draft
        if quote.status.value == "draft":
            quote = await quote_service.send(quote)
        
        return {"success": True, "message": "Devis envoyé par email"}
    else:
        return {"success": False, "message": "Erreur lors de l'envoi (vérifiez la configuration email)"}

