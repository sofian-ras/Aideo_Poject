# aideo/backend/app/api/auth.py (CORRIGÉ)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

# Imports BDD, Modèles et Services
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db_session
from app.models.base_models import User
from app.models.auth import UserCreate, Token, UserOut
import uuid

# Imports de Sécurité
from app.core.security import get_password_hash, verify_password, create_access_token

# Suppression de l'alias DB_Session pour éviter l'erreur de parsing de FastAPI lors du test
# DB_Session = Annotated[AsyncSession, Depends(get_db_session)] 

router = APIRouter()

# -------------------------------------------------------------------
# Route d'Inscription (POST /register)
# -------------------------------------------------------------------

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Inscription d'un nouvel utilisateur")
async def register_user(
    user_data: UserCreate, 
    # Injection directe de la dépendance (CORRECTION)
    db: AsyncSession = Depends(get_db_session)
):
    """
    Crée un nouvel utilisateur après vérification de l'unicité de l'email.
    """
    
    # 1. Vérification de l'unicité de l'email
    result = await db.execute(
        select(User).filter(User.email == user_data.email)
    )
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email est déjà enregistré."
        )

    # 2. Hachage du mot de passe
    hashed_password = get_password_hash(user_data.password)
    
    # 3. Création du nouvel utilisateur en BDD
    new_user = User(
        id=str(uuid.uuid4()), # Génération d'un UUID unique pour l'ID
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True
    )

    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        print(f"Erreur de BDD lors de l'inscription: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Échec de la création de l'utilisateur.")
    
    # 4. Retour des données utilisateur (sans le mot de passe)
    return new_user


# -------------------------------------------------------------------
# Route de Connexion (POST /login)
# -------------------------------------------------------------------

@router.post("/login", response_model=Token, summary="Connexion de l'utilisateur et obtention du jeton JWT")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    # Injection directe de la dépendance (CORRECTION)
    db: AsyncSession = Depends(get_db_session)
):
    """
    Authentifie l'utilisateur via email et mot de passe et retourne un jeton d'accès JWT.
    """
    
    # 1. Recherche de l'utilisateur par email (le 'username' dans le formulaire est l'email)
    result = await db.execute(
        select(User).filter(User.email == form_data.username)
    )
    user = result.scalars().first()

    # 2. Vérification de l'utilisateur et du mot de passe
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Création du jeton d'accès
    access_token = create_access_token(data={"sub": user.id})
    
    # 4. Retour du jeton
    return {"access_token": access_token, "token_type": "bearer"}