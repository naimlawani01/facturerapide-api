"""
Product service.
Handles product CRUD and stock management operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Service for product operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, owner: User, data: ProductCreate) -> Product:
        """
        Create a new product.
        
        Args:
            owner: Business owner
            data: Product data
            
        Returns:
            Created product
        """
        product = Product(
            owner_id=owner.id,
            **data.model_dump(),
        )
        
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        
        return product
    
    async def get_by_id(self, product_id: int, owner_id: int) -> Product | None:
        """
        Get product by ID, ensuring owner access.
        
        Args:
            product_id: Product ID
            owner_id: Owner's user ID
            
        Returns:
            Product if found and owned by user, None otherwise
        """
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_404(self, product_id: int, owner_id: int) -> Product:
        """
        Get product by ID or raise 404.
        
        Args:
            product_id: Product ID
            owner_id: Owner's user ID
            
        Returns:
            Product
            
        Raises:
            HTTPException: If product not found
        """
        product = await self.get_by_id(product_id, owner_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produit non trouvé",
            )
        return product
    
    async def list(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        is_service: bool | None = None,
        is_active: bool | None = None,
        low_stock_only: bool = False,
    ) -> tuple[list[Product], int]:
        """
        List products with pagination and filters.
        
        Args:
            owner_id: Owner's user ID
            skip: Number of records to skip
            limit: Maximum records to return
            search: Search term for name/SKU
            is_service: Filter by service type
            is_active: Filter by active status
            low_stock_only: Only show products with low stock
            
        Returns:
            Tuple of (products list, total count)
        """
        query = select(Product).where(Product.owner_id == owner_id)
        count_query = select(func.count(Product.id)).where(Product.owner_id == owner_id)
        
        # Apply filters
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (Product.name.ilike(search_filter)) |
                (Product.sku.ilike(search_filter))
            )
            count_query = count_query.where(
                (Product.name.ilike(search_filter)) |
                (Product.sku.ilike(search_filter))
            )
        
        if is_service is not None:
            query = query.where(Product.is_service == is_service)
            count_query = count_query.where(Product.is_service == is_service)
        
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
            count_query = count_query.where(Product.is_active == is_active)
        
        if low_stock_only:
            query = query.where(
                Product.is_service == False,
                Product.stock_quantity <= Product.low_stock_threshold,
            )
            count_query = count_query.where(
                Product.is_service == False,
                Product.stock_quantity <= Product.low_stock_threshold,
            )
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(Product.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        products = list(result.scalars().all())
        
        return products, total
    
    async def update(self, product: Product, data: ProductUpdate) -> Product:
        """
        Update product.
        
        Args:
            product: Product to update
            data: Update data
            
        Returns:
            Updated product
        """
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await self.db.flush()
        await self.db.refresh(product)
        
        return product
    
    async def update_stock(
        self,
        product: Product,
        quantity_change: int,
        reason: str | None = None,
    ) -> Product:
        """
        Update product stock quantity.
        
        Args:
            product: Product to update
            quantity_change: Positive to add, negative to remove
            reason: Reason for stock adjustment
            
        Returns:
            Updated product
            
        Raises:
            HTTPException: If product is a service or stock would go negative
        """
        if product.is_service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de gérer le stock d'un service",
            )
        
        new_quantity = product.stock_quantity + quantity_change
        
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuffisant (actuel: {product.stock_quantity})",
            )
        
        product.stock_quantity = new_quantity
        
        await self.db.flush()
        await self.db.refresh(product)
        
        return product
    
    async def delete(self, product: Product) -> None:
        """
        Delete product (soft delete by deactivating).
        
        Args:
            product: Product to delete
        """
        product.is_active = False
        await self.db.flush()

