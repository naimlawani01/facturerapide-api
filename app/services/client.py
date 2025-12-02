"""
Client service.
Handles client CRUD operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.client import Client
from app.models.user import User
from app.schemas.client import ClientCreate, ClientUpdate


class ClientService:
    """Service for client operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, owner: User, data: ClientCreate) -> Client:
        """
        Create a new client.
        
        Args:
            owner: Business owner
            data: Client data
            
        Returns:
            Created client
        """
        client = Client(
            owner_id=owner.id,
            **data.model_dump(),
        )
        
        self.db.add(client)
        await self.db.flush()
        await self.db.refresh(client)
        
        return client
    
    async def get_by_id(self, client_id: int, owner_id: int) -> Client | None:
        """
        Get client by ID, ensuring owner access.
        
        Args:
            client_id: Client ID
            owner_id: Owner's user ID
            
        Returns:
            Client if found and owned by user, None otherwise
        """
        result = await self.db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_404(self, client_id: int, owner_id: int) -> Client:
        """
        Get client by ID or raise 404.
        
        Args:
            client_id: Client ID
            owner_id: Owner's user ID
            
        Returns:
            Client
            
        Raises:
            HTTPException: If client not found
        """
        client = await self.get_by_id(client_id, owner_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
        return client
    
    async def list(
        self,
        owner_id: int,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[Client], int]:
        """
        List clients with pagination and search.
        
        Args:
            owner_id: Owner's user ID
            skip: Number of records to skip
            limit: Maximum records to return
            search: Search term for name/email
            
        Returns:
            Tuple of (clients list, total count)
        """
        query = select(Client).where(Client.owner_id == owner_id)
        count_query = select(func.count(Client.id)).where(Client.owner_id == owner_id)
        
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (Client.name.ilike(search_filter)) |
                (Client.email.ilike(search_filter))
            )
            count_query = count_query.where(
                (Client.name.ilike(search_filter)) |
                (Client.email.ilike(search_filter))
            )
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(Client.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        clients = list(result.scalars().all())
        
        return clients, total
    
    async def update(self, client: Client, data: ClientUpdate) -> Client:
        """
        Update client.
        
        Args:
            client: Client to update
            data: Update data
            
        Returns:
            Updated client
        """
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(client, field, value)
        
        await self.db.flush()
        await self.db.refresh(client)
        
        return client
    
    async def delete(self, client: Client) -> None:
        """
        Delete client.
        
        Args:
            client: Client to delete
            
        Note:
            Will fail if client has invoices (RESTRICT constraint)
        """
        try:
            await self.db.delete(client)
            await self.db.flush()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de supprimer ce client (factures existantes)",
            )

