from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from typing import Optional, Dict, Any

# IMPORTS CORRIGÉS
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.base_models import User # Pour le typage de la fonction de dépendance

# --- 1. Configuration des secrets et algorithmes ---

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CLE_SECRETE_TRES_COMPLEXE_A_REMPLACER_EN_PROD")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# --- 2. Fonctions de Hachage des Mots de Passe ---

def get_password_hash(password: str) -> str:
    return password_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)

# --- 3. Fonctions de Gestion des Jetons JWT ---

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Jeton invalide ou expiré: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- 4. Fonction de Dépendance pour FastAPI ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login") 

async def get_current_user_from_token(token: str, db_session: AsyncSession) -> User:
    """
    Dépendance FastAPI : Décode le jeton et récupère l'utilisateur en BDD.
    """
    
    # 1. Décodage et Validation du jeton
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub") 
        if user_id is None:
            raise JWTError("Payload invalide")
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou format incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Récupération de l'utilisateur en BDD
    result = await db_session.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur non trouvé.")
        
    return user