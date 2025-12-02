"""
Dashboard Service.
Provides statistics and analytics for the business.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceStatus
from app.models.quote import Quote, QuoteStatus
from app.models.payment import Payment
from app.models.client import Client
from app.models.product import Product


class DashboardService:
    """Service for dashboard statistics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_overview(self, owner_id: int) -> Dict[str, Any]:
        """
        Get business overview statistics.
        
        Returns:
            Overview with revenue, counts, and pending amounts
        """
        # Total revenue (paid invoices)
        revenue_result = await self.db.execute(
            select(func.sum(Invoice.amount_paid)).where(
                Invoice.owner_id == owner_id,
            )
        )
        total_revenue = revenue_result.scalar() or Decimal("0.00")
        
        # Pending invoices amount
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
        
        # Counts
        invoice_count = await self.db.execute(
            select(func.count(Invoice.id)).where(Invoice.owner_id == owner_id)
        )
        quote_count = await self.db.execute(
            select(func.count(Quote.id)).where(Quote.owner_id == owner_id)
        )
        client_count = await self.db.execute(
            select(func.count(Client.id)).where(Client.owner_id == owner_id)
        )
        product_count = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.owner_id == owner_id,
                Product.is_active == True,
            )
        )
        
        # Overdue invoices
        overdue_result = await self.db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.owner_id == owner_id,
                Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID]),
                Invoice.due_date < date.today(),
            )
        )
        overdue_count = overdue_result.scalar() or 0
        
        return {
            "total_revenue": float(total_revenue),
            "pending_amount": float(pending_amount),
            "invoice_count": invoice_count.scalar() or 0,
            "quote_count": quote_count.scalar() or 0,
            "client_count": client_count.scalar() or 0,
            "product_count": product_count.scalar() or 0,
            "overdue_invoice_count": overdue_count,
        }
    
    async def get_revenue_by_month(
        self,
        owner_id: int,
        year: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Get monthly revenue for the year.
        
        Args:
            owner_id: User ID
            year: Year to get data for (defaults to current year)
            
        Returns:
            List of monthly revenue data
        """
        if year is None:
            year = date.today().year
        
        monthly_data = []
        
        for month in range(1, 13):
            result = await self.db.execute(
                select(func.sum(Payment.amount))
                .join(Invoice)
                .where(
                    Invoice.owner_id == owner_id,
                    extract('year', Payment.payment_date) == year,
                    extract('month', Payment.payment_date) == month,
                )
            )
            amount = result.scalar() or Decimal("0.00")
            
            monthly_data.append({
                "month": month,
                "year": year,
                "revenue": float(amount),
            })
        
        return monthly_data
    
    async def get_invoice_status_distribution(
        self,
        owner_id: int,
    ) -> Dict[str, int]:
        """Get invoice count by status."""
        distribution = {}
        
        for status in InvoiceStatus:
            result = await self.db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.owner_id == owner_id,
                    Invoice.status == status,
                )
            )
            distribution[status.value] = result.scalar() or 0
        
        return distribution
    
    async def get_quote_status_distribution(
        self,
        owner_id: int,
    ) -> Dict[str, int]:
        """Get quote count by status."""
        distribution = {}
        
        for status in QuoteStatus:
            result = await self.db.execute(
                select(func.count(Quote.id)).where(
                    Quote.owner_id == owner_id,
                    Quote.status == status,
                )
            )
            distribution[status.value] = result.scalar() or 0
        
        return distribution
    
    async def get_top_clients(
        self,
        owner_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get top clients by revenue.
        
        Args:
            owner_id: User ID
            limit: Number of clients to return
            
        Returns:
            List of top clients with total revenue
        """
        result = await self.db.execute(
            select(
                Client.id,
                Client.name,
                func.sum(Invoice.amount_paid).label('total_revenue'),
                func.count(Invoice.id).label('invoice_count'),
            )
            .join(Invoice, Invoice.client_id == Client.id)
            .where(Client.owner_id == owner_id)
            .group_by(Client.id, Client.name)
            .order_by(func.sum(Invoice.amount_paid).desc())
            .limit(limit)
        )
        
        clients = []
        for row in result:
            clients.append({
                "id": row.id,
                "name": row.name,
                "total_revenue": float(row.total_revenue or 0),
                "invoice_count": row.invoice_count,
            })
        
        return clients
    
    async def get_top_products(
        self,
        owner_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get top products by sales.
        
        Args:
            owner_id: User ID
            limit: Number of products to return
            
        Returns:
            List of top products with total sales
        """
        from app.models.invoice import InvoiceItem
        
        result = await self.db.execute(
            select(
                Product.id,
                Product.name,
                func.sum(InvoiceItem.quantity).label('total_quantity'),
                func.sum(InvoiceItem.subtotal).label('total_revenue'),
            )
            .join(InvoiceItem, InvoiceItem.product_id == Product.id)
            .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .where(
                Product.owner_id == owner_id,
                Invoice.status.in_([InvoiceStatus.PAID, InvoiceStatus.PARTIALLY_PAID]),
            )
            .group_by(Product.id, Product.name)
            .order_by(func.sum(InvoiceItem.subtotal).desc())
            .limit(limit)
        )
        
        products = []
        for row in result:
            products.append({
                "id": row.id,
                "name": row.name,
                "total_quantity": float(row.total_quantity or 0),
                "total_revenue": float(row.total_revenue or 0),
            })
        
        return products
    
    async def get_recent_activity(
        self,
        owner_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent invoices and quotes.
        
        Args:
            owner_id: User ID
            limit: Number of items to return
            
        Returns:
            List of recent activities
        """
        activities = []
        
        # Recent invoices with client
        invoice_result = await self.db.execute(
            select(Invoice)
            .options(selectinload(Invoice.client))
            .where(Invoice.owner_id == owner_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        for invoice in invoice_result.scalars():
            activities.append({
                "type": "invoice",
                "id": invoice.id,
                "number": invoice.invoice_number,
                "client_name": invoice.client.name if invoice.client else "Client inconnu",
                "status": invoice.status.value,
                "amount": float(invoice.total),
                "date": invoice.created_at.isoformat(),
            })
        
        # Recent quotes with client
        quote_result = await self.db.execute(
            select(Quote)
            .options(selectinload(Quote.client))
            .where(Quote.owner_id == owner_id)
            .order_by(Quote.created_at.desc())
            .limit(limit)
        )
        for quote in quote_result.scalars():
            activities.append({
                "type": "quote",
                "id": quote.id,
                "number": quote.quote_number,
                "client_name": quote.client.name if quote.client else "Client inconnu",
                "status": quote.status.value,
                "amount": float(quote.total),
                "date": quote.created_at.isoformat(),
            })
        
        # Sort by date and limit
        activities.sort(key=lambda x: x["date"], reverse=True)
        return activities[:limit]
    
    async def get_low_stock_products(
        self,
        owner_id: int,
    ) -> List[Dict[str, Any]]:
        """Get products with low stock."""
        result = await self.db.execute(
            select(Product)
            .where(
                Product.owner_id == owner_id,
                Product.is_active == True,
                Product.is_service == False,
                Product.stock_quantity <= Product.low_stock_threshold,
            )
            .order_by(Product.stock_quantity.asc())
        )
        
        products = []
        for product in result.scalars():
            products.append({
                "id": product.id,
                "name": product.name,
                "stock_quantity": product.stock_quantity,
                "low_stock_threshold": product.low_stock_threshold,
            })
        
        return products
    
    async def get_full_dashboard(self, owner_id: int) -> Dict[str, Any]:
        """
        Get complete dashboard data.
        
        Returns all dashboard statistics in one call.
        """
        return {
            "overview": await self.get_overview(owner_id),
            "revenue_by_month": await self.get_revenue_by_month(owner_id),
            "invoice_distribution": await self.get_invoice_status_distribution(owner_id),
            "quote_distribution": await self.get_quote_status_distribution(owner_id),
            "top_clients": await self.get_top_clients(owner_id),
            "top_products": await self.get_top_products(owner_id),
            "recent_activity": await self.get_recent_activity(owner_id),
            "low_stock_products": await self.get_low_stock_products(owner_id),
        }

