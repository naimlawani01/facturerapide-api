"""
Payment service.
Handles payment creation and invoice status updates.
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
import logging

from app.models.payment import Payment, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.models.client import Client
from app.models.user import User
from app.schemas.payment import PaymentCreate
from app.services.email import EmailService

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, owner_id: int, data: PaymentCreate) -> Payment:
        """
        Create a payment for an invoice.
        
        Args:
            owner_id: Owner's user ID (for verification)
            data: Payment data
            
        Returns:
            Created payment
        """
        # Verify invoice belongs to owner and can receive payments
        invoice_result = await self.db.execute(
            select(Invoice)
            .options(selectinload(Invoice.client), selectinload(Invoice.owner))
            .where(
                Invoice.id == data.invoice_id,
                Invoice.owner_id == owner_id,
            )
        )
        invoice = invoice_result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture non trouvée",
            )
        
        if invoice.status == InvoiceStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de payer une facture annulée",
            )
        
        if invoice.status == InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de payer une facture brouillon",
            )
        
        if invoice.is_fully_paid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette facture est déjà entièrement payée",
            )
        
        # Check if payment exceeds balance
        if data.amount > invoice.balance_due:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le montant dépasse le solde dû ({invoice.balance_due})",
            )
        
        # Create payment
        payment = Payment(
            invoice_id=invoice.id,
            amount=data.amount,
            payment_date=data.payment_date,
            payment_method=data.payment_method,
            reference=data.reference,
            notes=data.notes,
        )
        
        self.db.add(payment)
        await self.db.flush()
        
        # Update invoice amount_paid
        invoice.amount_paid += data.amount
        
        # Update invoice status
        if invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        
        await self.db.flush()
        await self.db.refresh(payment)
        await self.db.refresh(invoice)  # Refresh invoice to ensure all relationships are loaded
        
        # Send payment receipt email automatically (non-blocking)
        # This is done in a separate try/except to ensure payment is always created
        # even if email fails
        try:
            # Double-check that client and owner are loaded
            if invoice.client and invoice.client.email and invoice.owner:
                email_service = EmailService()
                email_sent = await email_service.send_payment_receipt(
                    invoice=invoice,
                    payment=payment,
                    owner=invoice.owner,
                    client=invoice.client,
                )
                if email_sent:
                    logger.info(f"Reçu de paiement envoyé pour la facture {invoice.invoice_number}")
                else:
                    logger.warning(f"Échec de l'envoi du reçu pour la facture {invoice.invoice_number} (email non configuré ou erreur SMTP)")
            else:
                logger.warning(f"Impossible d'envoyer le reçu: client={invoice.client is not None}, email={invoice.client.email if invoice.client else None}, owner={invoice.owner is not None}")
        except Exception as e:
            # Don't fail payment creation if email fails
            # Log error but continue - payment is already saved
            logger.error(
                f"Erreur lors de l'envoi du reçu pour la facture {invoice.invoice_number}: {e}",
                exc_info=True
            )
        
        # Always return payment, even if email failed
        return payment
    
    async def get_by_id(self, payment_id: int, owner_id: int) -> Payment | None:
        """Get payment by ID, ensuring owner access through invoice."""
        result = await self.db.execute(
            select(Payment)
            .join(Invoice)
            .where(
                Payment.id == payment_id,
                Invoice.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_404(self, payment_id: int, owner_id: int) -> Payment:
        """Get payment by ID or raise 404."""
        payment = await self.get_by_id(payment_id, owner_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paiement non trouvé",
            )
        return payment
    
    async def list_by_invoice(
        self,
        invoice_id: int,
        owner_id: int,
    ) -> list[Payment]:
        """List all payments for an invoice."""
        # Verify invoice belongs to owner
        invoice_result = await self.db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.owner_id == owner_id,
            )
        )
        if not invoice_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture non trouvée",
            )
        
        result = await self.db.execute(
            select(Payment)
            .where(Payment.invoice_id == invoice_id)
            .order_by(Payment.payment_date.desc())
        )
        return list(result.scalars().all())
    
    async def list(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 20,
        from_date: date | None = None,
        to_date: date | None = None,
        payment_method: PaymentMethod | None = None,
    ) -> tuple[list[Payment], int]:
        """List all payments with pagination and filters."""
        query = (
            select(Payment)
            .join(Invoice)
            .where(Invoice.owner_id == owner_id)
        )
        count_query = (
            select(func.count(Payment.id))
            .join(Invoice)
            .where(Invoice.owner_id == owner_id)
        )
        
        # Apply filters
        if from_date:
            query = query.where(Payment.payment_date >= from_date)
            count_query = count_query.where(Payment.payment_date >= from_date)
        
        if to_date:
            query = query.where(Payment.payment_date <= to_date)
            count_query = count_query.where(Payment.payment_date <= to_date)
        
        if payment_method:
            query = query.where(Payment.payment_method == payment_method)
            count_query = count_query.where(Payment.payment_method == payment_method)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        payments = list(result.scalars().all())
        
        return payments, total
    
    async def delete(self, payment: Payment) -> None:
        """
        Delete a payment and update invoice.
        
        Note: This is typically not allowed in production for audit reasons.
        Consider marking as cancelled instead.
        """
        # Get the invoice
        invoice_result = await self.db.execute(
            select(Invoice).where(Invoice.id == payment.invoice_id)
        )
        invoice = invoice_result.scalar_one()
        
        # Update invoice amount
        invoice.amount_paid -= payment.amount
        
        # Update status
        if invoice.amount_paid <= 0:
            invoice.status = InvoiceStatus.SENT
            invoice.amount_paid = Decimal("0.00")
        elif invoice.amount_paid < invoice.total:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        
        await self.db.delete(payment)
        await self.db.flush()
    
    async def get_stats(
        self,
        owner_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        """Get payment statistics."""
        query = (
            select(Payment)
            .join(Invoice)
            .where(Invoice.owner_id == owner_id)
        )
        
        if from_date:
            query = query.where(Payment.payment_date >= from_date)
        if to_date:
            query = query.where(Payment.payment_date <= to_date)
        
        # Total by payment method
        method_totals = {}
        for method in PaymentMethod:
            result = await self.db.execute(
                select(func.sum(Payment.amount))
                .join(Invoice)
                .where(
                    Invoice.owner_id == owner_id,
                    Payment.payment_method == method,
                )
            )
            method_totals[method.value] = result.scalar() or Decimal("0.00")
        
        # Total amount
        total_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .join(Invoice)
            .where(Invoice.owner_id == owner_id)
        )
        total_amount = total_result.scalar() or Decimal("0.00")
        
        return {
            "by_method": method_totals,
            "total": total_amount,
        }

