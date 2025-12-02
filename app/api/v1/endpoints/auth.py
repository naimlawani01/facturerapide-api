"""
Authentication endpoints.
Login, register, refresh token.
"""

from fastapi import APIRouter, status

from app.api.deps import DbSession, CurrentUser
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenPair,
    RefreshTokenRequest,
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription",
    description="Créer un nouveau compte utilisateur",
)
async def register(
    data: RegisterRequest,
    db: DbSession,
) -> UserResponse:
    """Inscription d'un nouvel utilisateur."""
    service = AuthService(db)
    user = await service.register(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Connexion",
    description="Se connecter avec email et mot de passe",
)
async def login(
    data: LoginRequest,
    db: DbSession,
) -> TokenPair:
    """Connexion et obtention des tokens JWT."""
    service = AuthService(db)
    _, tokens = await service.login(data)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rafraîchir le token",
    description="Obtenir de nouveaux tokens avec le refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: DbSession,
) -> TokenPair:
    """Rafraîchir les tokens JWT."""
    service = AuthService(db)
    return await service.refresh_token(data.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil actuel",
    description="Obtenir les informations de l'utilisateur connecté",
)
async def get_current_user(
    current_user: CurrentUser,
) -> UserResponse:
    """Récupérer le profil de l'utilisateur connecté."""
    return UserResponse.model_validate(current_user)
