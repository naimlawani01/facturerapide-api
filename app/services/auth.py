"""
Authentication service.
Handles user registration, login, and token management.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_token_pair,
    decode_token,
    create_access_token,
    TokenPair,
)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register(self, data: RegisterRequest) -> User:
        """
        Register a new user.
        
        Args:
            data: Registration data
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un compte avec cet email existe déjà",
            )
        
        # Create user
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            business_name=data.business_name,
            business_phone=data.business_phone,
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def login(self, data: LoginRequest) -> tuple[User, TokenPair]:
        """
        Authenticate user and generate tokens.
        
        Args:
            data: Login credentials
            
        Returns:
            Tuple of (user, token_pair)
            
        Raises:
            HTTPException: If credentials are invalid
        """
        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte désactivé",
            )
        
        # Generate tokens
        token_pair = create_token_pair(user.id, user.email)
        
        return user, token_pair
    
    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """
        Generate new token pair from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token pair
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        # Decode refresh token
        token_data = decode_token(refresh_token)
        
        if token_data is None or token_data.token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de rafraîchissement invalide",
            )
        
        # Verify user still exists and is active
        result = await self.db.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé",
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte désactivé",
            )
        
        # Generate new token pair
        return create_token_pair(user.id, user.email)
    
    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

