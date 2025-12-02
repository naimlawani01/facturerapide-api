"""
API Dependencies.
Common dependencies for authentication, database sessions, etc.
"""

import logging
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User


# Logger
logger = logging.getLogger(__name__)

# Schéma de sécurité Bearer Token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Récupère l'utilisateur courant à partir du token JWT.
    
    Args:
        credentials: Token Bearer JWT
        db: Session de base de données
        
    Returns:
        Instance User de l'utilisateur authentifié
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur non trouvé
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token d'authentification invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        logger.warning("Tentative d'accès sans token")
        raise credentials_exception
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    if token_data is None:
        logger.warning("Token invalide ou expiré")
        raise credentials_exception
    
    if token_data.token_type != "access":
        logger.warning("Type de token invalide")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = token_data.user_id
    if user_id is None:
        logger.warning("Token sans identifiant utilisateur")
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"Utilisateur {user_id} non trouvé")
        raise credentials_exception
    
    logger.debug(f"Utilisateur authentifié: {user.email}")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Récupère l'utilisateur courant actif.
    
    Raises:
        HTTPException: Si le compte est désactivé
    """
    if not current_user.is_active:
        logger.warning(f"Compte désactivé: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    return current_user


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
