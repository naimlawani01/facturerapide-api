"""
User management endpoints.
Profile update, password change.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession, CurrentUser
from app.schemas.user import UserUpdate, UserResponse
from app.schemas.base import MessageResponse
from app.services.user import UserService


router = APIRouter()


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Mon profil",
    description="Obtenir mon profil utilisateur",
)
async def get_my_profile(
    current_user: CurrentUser,
) -> UserResponse:
    """Get current user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Mettre à jour mon profil",
    description="Mettre à jour les informations de mon profil",
)
async def update_my_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Update current user's profile."""
    service = UserService(db)
    user = await service.update(current_user, data)
    return UserResponse.model_validate(user)


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Changer le mot de passe",
    description="Changer mon mot de passe",
)
async def change_password(
    data: PasswordChangeRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Change current user's password."""
    service = UserService(db)
    await service.change_password(
        current_user,
        data.current_password,
        data.new_password,
    )
    return MessageResponse(message="Mot de passe modifié avec succès")

