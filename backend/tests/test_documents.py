# aideo/backend/tests/test_documents.py

from httpx import AsyncClient
import pytest
from app.core.security import get_password_hash # Pour hacher le mot de passe de l'utilisateur de test
from app.models.base_models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import Dict, Any

# --- Données de test (identiques à celles de test_auth.py) ---
TEST_EMAIL = "doc_test@aideo.com"
TEST_PASSWORD = "DocPassword123"
TEST_FILE_CONTENT = b"Ceci est le contenu d'un document de test simple pour l'OCR."
TEST_FILENAME = "facture_test.pdf"

# --- Fixtures de session et client HTTP fournies par conftest.py ---

# --- Fixture d'Utilisateur et de Jeton de Test ---

@pytest.fixture(scope="module")
async def authenticated_user_token(db_test_session: AsyncSession) -> Dict[str, str]:
    """
    Crée un utilisateur dans la BDD de test et retourne son jeton JWT.
    Cette fixture s'exécute une seule fois par module de test.
    """
    
    # 1. Création de l'utilisateur de test si non existant
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(TEST_PASSWORD)
    
    new_user = User(
        id=user_id,
        email=TEST_EMAIL,
        hashed_password=hashed_password,
        is_active=True
    )
    
    try:
        db_test_session.add(new_user)
        await db_test_session.commit()
        await db_test_session.refresh(new_user)
    except Exception as e:
        print(f"Erreur de création d'utilisateur de test: {e}")
        await db_test_session.rollback()

    # 2. Récupération du jeton via la route de connexion
    # Note: On crée un client temporaire car le client fixture est scope="session"
    async with AsyncClient(base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
        )
    
    if response.status_code != 200:
        raise Exception("Échec de la connexion pour obtenir le jeton de test.")
        
    return {
        "user_id": user_id,
        "token": response.json()["access_token"],
        "headers": {"Authorization": f"Bearer {response.json()['access_token']}"}
    }


# ----------------------------------------------------------------------
# A. TESTS DES OPÉRATIONS CRUD (DOCUMENTS)
# ----------------------------------------------------------------------

# L'ordre des tests est important ici pour tester le cycle de vie complet

# Stockage de l'ID du document créé pour les tests suivants
created_document_id = None


# Test 1 : POST /scan (Création/Upload)
async def test_1_create_document(client: AsyncClient, authenticated_user_token: Dict[str, Any]):
    """Teste l'upload d'un document et sa sauvegarde en BDD."""
    global created_document_id
    
    # 1. Requête POST avec le fichier de test
    response = await client.post(
        "/api/v1/documents/scan",
        headers=authenticated_user_token["headers"], # Utilisation du jeton JWT
        files={"file": (TEST_FILENAME, TEST_FILE_CONTENT, "application/pdf")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 2. Vérification de la réponse
    assert data["filename"] == TEST_FILENAME
    assert data["status"] == "success"
    assert "document_id" in data
    
    created_document_id = data["document_id"]
    assert created_document_id is not None
    print(f"\nDocument créé avec l'ID: {created_document_id}")


# Test 2 : GET / (Liste des documents)
async def test_2_list_documents(client: AsyncClient, authenticated_user_token: Dict[str, Any]):
    """Teste la récupération de la liste des documents de l'utilisateur."""
    
    response = await client.get(
        "/api/v1/documents/",
        headers=authenticated_user_token["headers"],
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Vérification qu'au moins un document (celui que nous venons de créer) est présent
    assert len(data) >= 1
    assert any(doc["id"] == created_document_id for doc in data)


# Test 3 : GET /{document_id} (Récupération détaillée)
async def test_3_get_document_details(client: AsyncClient, authenticated_user_token: Dict[str, Any]):
    """Teste la récupération des détails d'un document spécifique."""
    
    # 1. Requête GET pour le document créé
    response = await client.get(
        f"/api/v1/documents/{created_document_id}",
        headers=authenticated_user_token["headers"],
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 2. Vérification des champs
    assert data["id"] == created_document_id
    assert data["file_name"] == TEST_FILENAME
    assert "raw_text" in data # Le texte brut doit être présent
    assert "download_url" in data # L'URL pré-signée doit être présente


# Test 4 : PATCH /{document_id} (Mise à jour/Renommage)
async def test_4_update_document(client: AsyncClient, authenticated_user_token: Dict[str, Any]):
    """Teste la mise à jour des métadonnées (renommage)."""
    
    NEW_FILENAME = "facture_renommee.pdf"
    
    # 1. Requête PATCH
    response = await client.patch(
        f"/api/v1/documents/{created_document_id}",
        headers=authenticated_user_token["headers"],
        json={"file_name": NEW_FILENAME}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 2. Vérification de la réponse
    assert data["id"] == created_document_id
    assert data["file_name"] == NEW_FILENAME


# Test 5 : DELETE /{document_id} (Suppression)
async def test_5_delete_document(client: AsyncClient, authenticated_user_token: Dict[str, Any]):
    """Teste la suppression du document (Base de données et MinIO/S3)."""
    
    # 1. Requête DELETE
    response = await client.delete(
        f"/api/v1/documents/{created_document_id}",
        headers=authenticated_user_token["headers"],
    )
    
    # 2. Vérification du statut 204 No Content
    assert response.status_code == 204
    assert response.text == ""

    # 3. Vérification que le document a bien été supprimé (Requête GET suivante doit échouer)
    response_check = await client.get(
        f"/api/v1/documents/{created_document_id}",
        headers=authenticated_user_token["headers"],
    )
    assert response_check.status_code == 404


# ----------------------------------------------------------------------
# B. TESTS DE SÉCURITÉ (ACCÈS NON AUTORISÉ)
# ----------------------------------------------------------------------

# Test 6 : GET / (Accès non autorisé)
async def test_6_unauthorized_access(client: AsyncClient):
    """Teste l'accès à une route sécurisée sans jeton (403/401)."""
    
    response = await client.get("/api/v1/documents/")
    
    # L'authentification par dépendance doit renvoyer 401 Unauthorized
    assert response.status_code == 401
    assert "Jeton invalide" in response.json()["detail"] or "Not authenticated" in response.json()["detail"]