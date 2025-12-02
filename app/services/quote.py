"""
Quote service.
Handles quote CRUD, line items, and conversion to invoice.
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.quote import Quote, QuoteItem, QuoteStatus
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.client import Client
from app.models.product import Product
from app.models.user import User
from app.schemas.quote import (
    QuoteCreate,
    QuoteUpdate,
    QuoteItemCreate,
)


class QuoteService:
    """Service for quote operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def _generate_quote_number(self, owner_id: int) -> str:
        """
        Generate unique quote number.
        Format: DEVIS-{year}-{sequence}
        """
        current_year = date.today().year
        prefix = f"DEV-{current_year}-"
        
        result = await self.db.execute(
            select(func.count(Quote.id)).where(
                Quote.owner_id == owner_id,
                Quote.quote_number.like(f"{prefix}%"),
            )
        )
        count = result.scalar() or 0
        
        return f"{prefix}{str(count + 1).zfill(5)}"
    
    async def create(self, owner: User, data: QuoteCreate) -> Quote:
        """
        Create a new quote with items.
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
        
        # Generate quote number
        quote_number = await self._generate_quote_number(owner.id)
        
        # Create quote
        quote = Quote(
            owner_id=owner.id,
            client_id=data.client_id,
            quote_number=quote_number,
            issue_date=data.issue_date,
            validity_date=data.validity_date,
            notes=data.notes,
            terms=data.terms,
            status=QuoteStatus.DRAFT,
        )
        
        self.db.add(quote)
        await self.db.flush()
        
        # Add items
        for item_data in data.items:
            item = await self._create_item(quote, item_data, owner.id)
            quote.items.append(item)
        
        # Calculate totals
        quote.calculate_totals()
        
        await self.db.flush()
        await self.db.refresh(quote)
        
        return quote
    
    async def _create_item(
        self,
        quote: Quote,
        data: QuoteItemCreate,
        owner_id: int,
    ) -> QuoteItem:
        """Create a quote item, optionally from a product."""
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
            
            item = QuoteItem(
                quote_id=quote.id,
                product_id=product.id,
                description=data.description or product.name,
                quantity=data.quantity,
                unit=data.unit or product.unit,
                unit_price=data.unit_price if data.unit_price else product.unit_price,
                tax_rate=data.tax_rate if data.tax_rate else product.tax_rate,
                discount_percent=data.discount_percent,
            )
        else:
            item = QuoteItem(
                quote_id=quote.id,
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
    
    async def get_by_id(self, quote_id: int, owner_id: int) -> Quote | None:
        """Get quote by ID with all relationships loaded."""
        result = await self.db.execute(
            select(Quote)
            .options(
                selectinload(Quote.items),
                selectinload(Quote.client),
            )
            .where(
                Quote.id == quote_id,
                Quote.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_404(self, quote_id: int, owner_id: int) -> Quote:
        """Get quote by ID or raise 404."""
        quote = await self.get_by_id(quote_id, owner_id)
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devis non trouvé",
            )
        return quote
    
    async def list(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 20,
        status: QuoteStatus | None = None,
        client_id: int | None = None,
    ) -> tuple[list[Quote], int]:
        """List quotes with pagination and filters."""
        query = select(Quote).where(Quote.owner_id == owner_id)
        count_query = select(func.count(Quote.id)).where(Quote.owner_id == owner_id)
        
        if status:
            query = query.where(Quote.status == status)
            count_query = count_query.where(Quote.status == status)
        
        if client_id:
            query = query.where(Quote.client_id == client_id)
            count_query = count_query.where(Quote.client_id == client_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = (
            query
            .options(
                selectinload(Quote.items),
                selectinload(Quote.client),
            )
            .order_by(Quote.issue_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        quotes = list(result.scalars().all())
        
        return quotes, total
    
    async def update(self, quote: Quote, data: QuoteUpdate) -> Quote:
        """Update quote. Only allowed for DRAFT quotes."""
        if quote.status not in [QuoteStatus.DRAFT]:
            if data.status is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de modifier un devis envoyé",
                )
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(quote, field, value)
        
        await self.db.flush()
        await self.db.refresh(quote)
        
        return quote
    
    async def add_item(
        self,
        quote: Quote,
        data: QuoteItemCreate,
        owner_id: int,
    ) -> Quote:
        """Add an item to a quote."""
        if quote.status != QuoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de modifier un devis non brouillon",
            )
        
        item = await self._create_item(quote, data, owner_id)
        await self.db.flush()
        await self.db.refresh(quote)
        quote.calculate_totals()
        await self.db.flush()
        
        return quote
    
    async def remove_item(self, quote: Quote, item_id: int) -> Quote:
        """Remove an item from a quote."""
        if quote.status != QuoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de modifier un devis non brouillon",
            )
        
        item = next((i for i in quote.items if i.id == item_id), None)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ligne de devis non trouvée",
            )
        
        await self.db.delete(item)
        await self.db.flush()
        await self.db.refresh(quote)
        quote.calculate_totals()
        await self.db.flush()
        
        return quote
    
    async def send(self, quote: Quote) -> Quote:
        """Mark quote as sent."""
        if quote.status != QuoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les devis brouillon peuvent être envoyés",
            )
        
        if not quote.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'envoyer un devis sans lignes",
            )
        
        quote.status = QuoteStatus.SENT
        await self.db.flush()
        
        return quote
    
    async def accept(self, quote: Quote) -> Quote:
        """Mark quote as accepted."""
        if quote.status != QuoteStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les devis envoyés peuvent être acceptés",
            )
        
        quote.status = QuoteStatus.ACCEPTED
        await self.db.flush()
        
        return quote
    
    async def reject(self, quote: Quote) -> Quote:
        """Mark quote as rejected."""
        if quote.status != QuoteStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les devis envoyés peuvent être refusés",
            )
        
        quote.status = QuoteStatus.REJECTED
        await self.db.flush()
        
        return quote
    
    async def convert_to_invoice(self, quote: Quote, owner: User) -> Invoice:
        """
        Convert accepted quote to invoice.
        
        Creates a new invoice with the same items.
        """
        if quote.status != QuoteStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les devis acceptés peuvent être convertis en facture",
            )
        
        if quote.converted_invoice_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce devis a déjà été converti en facture",
            )
        
        # Generate invoice number
        current_year = date.today().year
        prefix = f"FACT-{current_year}-"
        result = await self.db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.owner_id == owner.id,
                Invoice.invoice_number.like(f"{prefix}%"),
            )
        )
        count = result.scalar() or 0
        invoice_number = f"{prefix}{str(count + 1).zfill(5)}"
        
        # Create invoice
        invoice = Invoice(
            owner_id=owner.id,
            client_id=quote.client_id,
            invoice_number=invoice_number,
            issue_date=date.today(),
            due_date=date.today(),  # Can be adjusted
            notes=quote.notes,
            terms=quote.terms,
            status=InvoiceStatus.DRAFT,
            subtotal=quote.subtotal,
            tax_total=quote.tax_total,
            total=quote.total,
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Copy items
        for quote_item in quote.items:
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=quote_item.product_id,
                description=quote_item.description,
                quantity=quote_item.quantity,
                unit=quote_item.unit,
                unit_price=quote_item.unit_price,
                tax_rate=quote_item.tax_rate,
                discount_percent=quote_item.discount_percent,
            )
            self.db.add(invoice_item)
        
        # Update quote status
        quote.status = QuoteStatus.CONVERTED
        quote.converted_invoice_id = invoice.id
        
        await self.db.flush()
        await self.db.refresh(invoice)
        
        return invoice
    
    async def get_stats(self, owner_id: int) -> dict:
        """Get quote statistics."""
        status_counts = {}
        for s in QuoteStatus:
            result = await self.db.execute(
                select(func.count(Quote.id)).where(
                    Quote.owner_id == owner_id,
                    Quote.status == s,
                )
            )
            status_counts[s.value] = result.scalar() or 0
        
        # Total value of accepted quotes
        accepted_result = await self.db.execute(
            select(func.sum(Quote.total)).where(
                Quote.owner_id == owner_id,
                Quote.status == QuoteStatus.ACCEPTED,
            )
        )
        total_accepted = accepted_result.scalar() or Decimal("0.00")
        
        # Conversion rate
        sent_count = status_counts.get("sent", 0) + status_counts.get("accepted", 0) + status_counts.get("rejected", 0) + status_counts.get("converted", 0)
        converted_count = status_counts.get("accepted", 0) + status_counts.get("converted", 0)
        conversion_rate = (converted_count / sent_count * 100) if sent_count > 0 else 0
        
        return {
            "status_counts": status_counts,
            "total_accepted_value": total_accepted,
            "conversion_rate": round(conversion_rate, 2),
        }

