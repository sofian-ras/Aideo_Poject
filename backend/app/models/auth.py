from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Schéma pour l'Inscription (Input)
class UserCreate(BaseModel):
    """Schéma des données requises pour l'inscription d'un nouvel utilisateur."""
    email: EmailStr = Field(..., example="jean.dupont@mail.com")
    password: str = Field(..., min_length=8, description="Le mot de passe doit contenir au moins 8 caractères.")

# Schéma pour la Connexion (Input)
# Nous utilisons les mêmes champs que UserCreate, mais nous le séparons pour la clarté.
class UserLogin(UserCreate):
    """Schéma des données requises pour la connexion."""
    pass

# Schéma pour le jeton de réponse (Output)
class Token(BaseModel):
    """Schéma de la réponse après une connexion réussie."""
    access_token: str
    token_type: str = "bearer"

# Schéma pour l'utilisateur dans le système (Output)
class UserOut(BaseModel):
    """Schéma des informations utilisateur à renvoyer (sans le mot de passe haché)."""
    id: str
    email: EmailStr
    is_active: bool
    
    class Config:
        from_attributes = True # Permet la conversion facile depuis le modèle SQLAlchemy (ORM)