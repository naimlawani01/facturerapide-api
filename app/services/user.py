"""
User service.
Handles user profile management.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserUpdate
from app.core.security import get_password_hash


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, user: User, data: UserUpdate) -> User:
        """
        Update user profile.
        
        Args:
            user: User to update
            data: Update data
            
        Returns:
            Updated user
        """
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Change user password.
        
        Args:
            user: User to update
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            Updated user
            
        Raises:
            HTTPException: If current password is incorrect
        """
        from app.core.security import verify_password
        
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect",
            )
        
        user.hashed_password = get_password_hash(new_password)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        return user

