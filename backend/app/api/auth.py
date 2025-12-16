from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy.future import select
import uuid

from app.dependencies import DB_SESSION_DEPENDENCY
from app.models.base_models import User
from app.models.auth import UserCreate, UserOut, Token
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)

router = APIRouter()


# -------------------------------------------------------------
# POST /auth/register
# -------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription utilisateur",
)
async def register_user(
    user_data: UserCreate,
    db=DB_SESSION_DEPENDENCY,
):
    result = await db.execute(select(User).filter(User.email == user_data.email))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


# -------------------------------------------------------------
# POST /auth/login
# -------------------------------------------------------------

@router.post(
    "/login",
    response_model=Token,
    summary="Connexion utilisateur",
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db=DB_SESSION_DEPENDENCY,
):
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}