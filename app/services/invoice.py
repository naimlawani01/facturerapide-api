"""
Invoice service.
Handles invoice CRUD, line items, and calculations.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.client import Client
from app.models.product import Product
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoiceItemUpdate,
)
from app.services.pdf import PDFService
from app.services.email import EmailService


class InvoiceService:
    """Service for invoice operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def _generate_invoice_number(self, owner_id: int) -> str:
        """
        Generate unique invoice number.
        Format: FACTURE-{year}-{sequence}
        """
        current_year = date.today().year
        prefix = f"FACT-{current_year}-"
        
        # Get count of invoices for this user this year
        result = await self.db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.owner_id == owner_id,
                Invoice.invoice_number.like(f"{prefix}%"),
            )
        )
        count = result.scalar() or 0
        
        return f"{prefix}{str(count + 1).zfill(5)}"
    
    async def create(self, owner: User, data: InvoiceCreate) -> Invoice:
        """
        Create a new invoice with items.
        
        Args:
            owner: Business owner
            data: Invoice data with items
            
        Returns:
            Created invoice
        """
        # Verify client belongs to owner
        client_result = await self.db.execute(
            select(Client).where(
                Client.id == data.client_id,
                Client.owner_id == owner.id,
            )
        )
        if not client_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
        
        # Generate invoice number
        invoice_number = await self._generate_invoice_number(owner.id)
        
        # Create invoice
        invoice = Invoice(
            owner_id=owner.id,
            client_id=data.client_id,
            invoice_number=invoice_number,
            issue_date=data.issue_date,
            due_date=data.due_date,
            notes=data.notes,
            terms=data.terms,
            status=InvoiceStatus.DRAFT,
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Add items
        items = []
        for item_data in data.items:
            item = await self._create_item(invoice, item_data, owner.id)
            items.append(item)
        
        await self.db.flush()
        
        # Calculate totals manually
        subtotal = sum(i.subtotal for i in items)
        tax_amount = sum(i.tax_amount for i in items)
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total = subtotal + tax_amount
        
        await self.db.flush()
        await self.db.refresh(invoice)
        
        return invoice
    
    async def _create_item(
        self,
        invoice: Invoice,
        data: InvoiceItemCreate,
        owner_id: int,
    ) -> InvoiceItem:
        """Create an invoice item, optionally from a product."""
        # If product_id provided, get product details
        if data.product_id:
            product_result = await self.db.execute(
                select(Product).where(
                    Product.id == data.product_id,
                    Product.owner_id == owner_id,
                )
            )
            product = product_result.scalar_one_or_none()
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Produit {data.product_id} non trouvé",
                )
            
            # Use product details if not overridden
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                description=data.description or product.name,
                quantity=data.quantity,
                unit=data.unit or product.unit,
                unit_price=data.unit_price if data.unit_price else product.unit_price,
                tax_rate=data.tax_rate if data.tax_rate else product.tax_rate,
                discount_percent=data.discount_percent,
            )
        else:
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=None,
                description=data.description,
                quantity=data.quantity,
                unit=data.unit,
                unit_price=data.unit_price,
                tax_rate=data.tax_rate,
                discount_percent=data.discount_percent,
            )
        
        self.db.add(item)
        return item
    
    async def get_by_id(self, invoice_id: int, owner_id: int) -> Invoice | None:
        """
        Get invoice by ID with all relationships loaded.
        """
        result = await self.db.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.items),
                selectinload(Invoice.payments),
                selectinload(Invoice.client),
            )
            .where(
                Invoice.id == invoice_id,
                Invoice.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_404(self, invoice_id: int, owner_id: int) -> Invoice:
        """Get invoice by ID or raise 404."""
        invoice = await self.get_by_id(invoice_id, owner_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture non trouvée",
            )
        return invoice
    
    async def list(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 20,
        status: InvoiceStatus | None = None,
        client_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[list[Invoice], int]:
        """
        List invoices with pagination and filters.
        """
        query = select(Invoice).where(Invoice.owner_id == owner_id)
        count_query = select(func.count(Invoice.id)).where(Invoice.owner_id == owner_id)
        
        # Apply filters
        if status:
            query = query.where(Invoice.status == status)
            count_query = count_query.where(Invoice.status == status)
        
        if client_id:
            query = query.where(Invoice.client_id == client_id)
            count_query = count_query.where(Invoice.client_id == client_id)
        
        if from_date:
            query = query.where(Invoice.issue_date >= from_date)
            count_query = count_query.where(Invoice.issue_date >= from_date)
        
        if to_date:
            query = query.where(Invoice.issue_date <= to_date)
            count_query = count_query.where(Invoice.issue_date <= to_date)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results with relationships
        query = (
            query
            .options(
                selectinload(Invoice.items),
                selectinload(Invoice.client),
            )
            .order_by(Invoice.issue_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        invoices = list(result.scalars().all())
        
        return invoices, total
    
    async def update(self, invoice: Invoice, data: InvoiceUpdate) -> Invoice:
        """
        Update invoice.
        Only allowed for DRAFT invoices (except status changes).
        """
        # Check if invoice can be modified
        if invoice.status not in [InvoiceStatus.DRAFT, InvoiceStatus.SENT]:
            if data.status is None:  # Only status change allowed
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de modifier une facture payée ou annulée",
                )
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(invoice, field, value)
        
        await self.db.flush()
        await self.db.refresh(invoice)
        
        return invoice
    
    async def add_item(
        self,
        invoice: Invoice,
        data: InvoiceItemCreate,
        owner_id: int,
    ) -> Invoice:
        """Add an item to an invoice."""
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de modifier une facture non brouillon",
            )
        
        item = await self._create_item(invoice, data, owner_id)
        await self.db.flush()
        
        # Refresh to get updated items
        await self.db.refresh(invoice)
        
        # Recalculate totals
        invoice.calculate_totals()
        await self.db.flush()
        
        return invoice
    
    async def remove_item(self, invoice: Invoice, item_id: int) -> Invoice:
        """Remove an item from an invoice."""
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de modifier une facture non brouillon",
            )
        
        # Find and remove item
        item = next((i for i in invoice.items if i.id == item_id), None)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ligne de facture non trouvée",
            )
        
        await self.db.delete(item)
        await self.db.flush()
        
        # Refresh to get updated items
        await self.db.refresh(invoice)
        
        # Recalculate totals
        invoice.calculate_totals()
        await self.db.flush()
        
        return invoice
    
    async def send(
        self,
        invoice: Invoice,
        owner: User,
        custom_message: str | None = None,
    ) -> Invoice:
        """
        Send invoice to client via email with PDF attachment.
        
        Args:
            invoice: Invoice to send
            owner: Business owner (for PDF header and email signature)
            custom_message: Optional custom message to include in email
            
        Returns:
            Updated invoice with SENT status
        """
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seules les factures brouillon peuvent être envoyées",
            )
        
        if not invoice.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'envoyer une facture sans lignes",
            )
        
        # Get client
        client = invoice.client
        if not client:
            result = await self.db.execute(
                select(Client).where(Client.id == invoice.client_id)
            )
            client = result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
        
        if not client.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le client n'a pas d'adresse email",
            )
        
        # Generate PDF
        pdf_service = PDFService()
        pdf_path = await pdf_service.generate_invoice_pdf(invoice, owner)
        
        # Store PDF path on invoice
        invoice.pdf_path = pdf_path
        
        # Send email
        email_service = EmailService()
        email_sent = await email_service.send_invoice(
            invoice=invoice,
            owner=owner,
            client=client,
            pdf_path=pdf_path,
            custom_message=custom_message,
        )
        
        if not email_sent:
            # Email non configuré - on met quand même à jour le statut
            # mais on log un warning (déjà fait dans EmailService)
            pass
        
        # Update invoice status
        invoice.status = InvoiceStatus.SENT
        invoice.sent_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        
        return invoice
    
    async def cancel(self, invoice: Invoice) -> Invoice:
        """Cancel an invoice."""
        if invoice.status == InvoiceStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'annuler une facture payée",
            )
        
        invoice.status = InvoiceStatus.CANCELLED
        await self.db.flush()
        
        return invoice
    
    async def delete(self, invoice: Invoice) -> None:
        """
        Delete an invoice.
        
        Only DRAFT invoices can be deleted.
        Sent/paid invoices should be cancelled instead for audit purposes.
        """
        if invoice.status != InvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seules les factures brouillon peuvent être supprimées. Utilisez l'annulation pour les autres.",
            )
        
        # Delete invoice (cascade will delete items and payments)
        await self.db.delete(invoice)
        await self.db.flush()
    
    async def update_payment_status(self, invoice: Invoice) -> Invoice:
        """
        Update invoice payment status based on payments.
        Called after payment is added.
        """
        if invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        
        await self.db.flush()
        return invoice
    
    async def get_stats(self, owner_id: int) -> dict:
        """Get invoice statistics for dashboard."""
        # Total invoices by status
        status_counts = {}
        for s in InvoiceStatus:
            result = await self.db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.owner_id == owner_id,
                    Invoice.status == s,
                )
            )
            status_counts[s.value] = result.scalar() or 0
        
        # Total revenue (paid invoices)
        revenue_result = await self.db.execute(
            select(func.sum(Invoice.total)).where(
                Invoice.owner_id == owner_id,
                Invoice.status == InvoiceStatus.PAID,
            )
        )
        total_revenue = revenue_result.scalar() or Decimal("0.00")
        
        # Pending amount (sent but not fully paid)
        pending_result = await self.db.execute(
            select(func.sum(Invoice.total - Invoice.amount_paid)).where(
                Invoice.owner_id == owner_id,
                Invoice.status.in_([
                    InvoiceStatus.SENT,
                    InvoiceStatus.PARTIALLY_PAID,
                    InvoiceStatus.OVERDUE,
                ]),
            )
        )
        pending_amount = pending_result.scalar() or Decimal("0.00")
        
        return {
            "status_counts": status_counts,
            "total_revenue": total_revenue,
            "pending_amount": pending_amount,
        }

