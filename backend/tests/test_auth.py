# aideo/backend/tests/test_auth.py

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.base_models import User

# Données d'utilisateur de test (doivent être différentes de celles dans test_documents.py pour l'isolation)
TEST_AUTH_EMAIL = "auth_test@aideo.com"
TEST_AUTH_PASSWORD = "AuthPassword123"

# Les fixtures (client et db_test_session) sont injectées automatiquement par pytest

# Test de l'inscription (Register)
async def test_register_user_auth(client: AsyncClient, db_test_session: AsyncSession):
    """Teste la création d'un nouvel utilisateur via la route /register."""
    
    # 1. Requête d'inscription
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": TEST_AUTH_EMAIL, "password": TEST_AUTH_PASSWORD}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # 2. Vérification de la réponse
    assert data["email"] == TEST_AUTH_EMAIL
    assert "id" in data
    
    # 3. Vérification en base de données
    result = await db_test_session.execute(select(User).filter(User.email == TEST_AUTH_EMAIL))
    user_in_db = result.scalars().first()
    
    assert user_in_db is not None
    assert user_in_db.email == TEST_AUTH_EMAIL


# Test de l'inscription d'un utilisateur existant (Conflit 409)
async def test_register_existing_user_auth(client: AsyncClient):
    """Teste le refus d'inscrire le même utilisateur deux fois."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": TEST_AUTH_EMAIL, "password": TEST_AUTH_PASSWORD}
    )
    # On s'attend à un conflit (409)
    assert response.status_code == 409
    assert "Cet email est déjà enregistré." in response.json()["detail"]


# Test de la connexion réussie (Login)
async def test_login_success_auth(client: AsyncClient):
    """Teste l'obtention du jeton d'accès avec les identifiants corrects."""
    
    # Utilise le format standard OAuth2 pour la connexion (form_data)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_AUTH_EMAIL, "password": TEST_AUTH_PASSWORD}
    )
    
    assert response.status_code == 200
    token_data = response.json()
    
    # Vérification de la structure du jeton
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


# Test de la connexion échouée (Identifiants incorrects 401)
async def test_login_failure_auth(client: AsyncClient):
    """Teste l'échec de la connexion avec un mot de passe incorrect."""
    
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": TEST_AUTH_EMAIL, "password": "WrongPassword"}
    )
    
    assert response.status_code == 401
    assert "Identifiants incorrects." in response.json()["detail"]