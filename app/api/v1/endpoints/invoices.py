"""
Invoice management endpoints.
CRUD operations for invoices and line items.
"""

from datetime import date
from fastapi import APIRouter, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import DbSession, CurrentUser
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceItemCreate,
)
from app.schemas.base import MessageResponse
from app.models.invoice import InvoiceStatus
from app.services.invoice import InvoiceService
from app.services.pdf import PDFService


router = APIRouter()


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une facture",
    description="Créer une nouvelle facture avec ses lignes",
)
async def create_invoice(
    data: InvoiceCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Create a new invoice."""
    service = InvoiceService(db)
    invoice = await service.create(current_user, data)
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "",
    response_model=InvoiceListResponse,
    summary="Lister les factures",
    description="Obtenir la liste paginée des factures",
)
async def list_invoices(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page"),
    status: InvoiceStatus | None = Query(None, description="Filtrer par statut"),
    client_id: int | None = Query(None, description="Filtrer par client"),
    from_date: date | None = Query(None, description="Date de début"),
    to_date: date | None = Query(None, description="Date de fin"),
) -> InvoiceListResponse:
    """List all invoices with pagination and filters."""
    service = InvoiceService(db)
    skip = (page - 1) * per_page
    
    invoices, total = await service.list(
        owner_id=current_user.id,
        skip=skip,
        limit=per_page,
        status=status,
        client_id=client_id,
        from_date=from_date,
        to_date=to_date,
    )
    
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/stats",
    summary="Statistiques des factures",
    description="Obtenir les statistiques des factures",
)
async def get_invoice_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get invoice statistics."""
    service = InvoiceService(db)
    return await service.get_stats(current_user.id)


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Détails d'une facture",
    description="Obtenir les détails d'une facture",
)
async def get_invoice(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Get invoice by ID."""
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    return InvoiceResponse.model_validate(invoice)


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Mettre à jour une facture",
    description="Mettre à jour les informations d'une facture",
)
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Update an invoice."""
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    invoice = await service.update(invoice, data)
    return InvoiceResponse.model_validate(invoice)


@router.delete(
    "/{invoice_id}",
    response_model=MessageResponse,
    summary="Supprimer une facture",
    description="Supprimer une facture (uniquement les brouillons)",
)
async def delete_invoice(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Delete an invoice (only DRAFT invoices)."""
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    await service.delete(invoice)
    return MessageResponse(message="Facture supprimée avec succès")


@router.post(
    "/{invoice_id}/items",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une ligne",
    description="Ajouter une ligne à une facture",
)
async def add_invoice_item(
    invoice_id: int,
    data: InvoiceItemCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Add an item to an invoice."""
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    invoice = await service.add_item(invoice, data, current_user.id)
    return InvoiceResponse.model_validate(invoice)


@router.delete(
    "/{invoice_id}/items/{item_id}",
    response_model=InvoiceResponse,
    summary="Supprimer une ligne",
    description="Supprimer une ligne d'une facture",
)
async def remove_invoice_item(
    invoice_id: int,
    item_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Remove an item from an invoice."""
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    invoice = await service.remove_item(invoice, item_id)
    return InvoiceResponse.model_validate(invoice)


class SendInvoiceRequest(BaseModel):
    """Request body for sending invoice."""
    message: str | None = None


@router.post(
    "/{invoice_id}/send",
    response_model=InvoiceResponse,
    summary="Envoyer la facture",
    description="Génère le PDF et envoie la facture par email au client",
)
async def send_invoice(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: SendInvoiceRequest | None = None,
) -> InvoiceResponse:
    """
    Send invoice to client via email.
    
    - Generates PDF
    - Sends email with PDF attached
    - Updates status to SENT
    """
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    
    custom_message = body.message if body else None
    invoice = await service.send(invoice, current_user, custom_message)
    
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    summary="Annuler une facture",
    description="Annuler une facture",
)
async def cancel_invoice(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InvoiceResponse:
    """Cancel an invoice."""
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    invoice = await service.cancel(invoice)
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/{invoice_id}/pdf",
    summary="Télécharger le PDF",
    description="Générer et télécharger la facture en PDF",
    response_class=FileResponse,
)
async def download_invoice_pdf(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Generate and download invoice PDF."""
    invoice_service = InvoiceService(db)
    invoice = await invoice_service.get_or_404(invoice_id, current_user.id)
    
    pdf_service = PDFService()
    pdf_path = await pdf_service.generate_invoice_pdf(invoice, current_user)
    
    # Update invoice with PDF path
    invoice.pdf_path = pdf_path
    await db.flush()
    
    return FileResponse(
        path=pdf_path,
        filename=f"facture_{invoice.invoice_number}.pdf",
        media_type="application/pdf",
    )


@router.post(
    "/{invoice_id}/send-email",
    response_model=InvoiceResponse,
    summary="Envoyer par email",
    description="Alias pour /send - Envoie la facture par email au client",
    deprecated=True,
)
async def send_invoice_email(
    invoice_id: int,
    current_user: CurrentUser,
    db: DbSession,
    body: SendInvoiceRequest | None = None,
) -> InvoiceResponse:
    """
    Envoyer la facture par email.
    
    Deprecated: Utilisez POST /{invoice_id}/send à la place.
    """
    service = InvoiceService(db)
    invoice = await service.get_or_404(invoice_id, current_user.id)
    
    custom_message = body.message if body else None
    invoice = await service.send(invoice, current_user, custom_message)
    
    return InvoiceResponse.model_validate(invoice)

