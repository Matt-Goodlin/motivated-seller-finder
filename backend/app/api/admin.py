"""Admin-only endpoints: user management, invite generation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User, Invite
from app.schemas.auth import InviteCreate, InviteOut, UserOut
from app.services.auth import require_admin, create_invite
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot deactivate admin accounts")
    user.is_active = False
    await db.commit()
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}/activate", response_model=UserOut)
async def activate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.commit()
    return UserOut.model_validate(user)


@router.post("/invites", response_model=InviteOut)
async def create_invite_link(
    body: InviteCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    invite = await create_invite(db, admin, email=body.email, expires_days=body.expires_days)
    invite_url = f"{settings.frontend_url}/register?token={invite.token}"
    return InviteOut(
        id=invite.id,
        token=invite.token,
        email=invite.email,
        expires_at=invite.expires_at,
        is_active=invite.is_active,
        used_at=invite.used_at,
        invite_url=invite_url,
    )


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Invite).order_by(Invite.expires_at.desc()).limit(100))
    invites = result.scalars().all()
    return [
        InviteOut(
            id=i.id,
            token=i.token,
            email=i.email,
            expires_at=i.expires_at,
            is_active=i.is_active,
            used_at=i.used_at,
            invite_url=f"{settings.frontend_url}/register?token={i.token}",
        )
        for i in invites
    ]


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Invite).where(Invite.id == invite_id))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.is_active = False
    await db.commit()
    return {"message": "Invite revoked"}
