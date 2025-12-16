# aideo/backend/tests/conftest.py

import os
import asyncio
import pytest
from httpx import AsyncClient
from app.main import app
from app.core.database import get_db_session, engine, AsyncSessionLocal
from app.models.base_models import Base
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

# 1. Préparation de l'environnement de test
# Force l'utilisation du moteur de test dans database.py (aideo_test_db)
os.environ["TESTING"] = "True" 

# Fixture de session BDD de test
@pytest.fixture(scope="session")
async def db_test_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Crée une session de base de données de test asynchrone pour les tests.
    """
    async with AsyncSessionLocal() as session:
        yield session

# Fixture de connexion au client API
@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Client HTTP asynchrone pour faire des requêtes à l'application FastAPI de test.
    """
    # Utilise l'application FastAPI pour les tests
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Fixture de sur-écriture de la dépendance BDD
@pytest.fixture(scope="session")
def override_get_db_session(db_test_session: AsyncSession):
    """
    Remplace la dépendance get_db_session par une session de test.
    """
    async def _get_db_session_override():
        yield db_test_session
    
    # Injection de dépendance pour que l'API utilise la BDD de test
    app.dependency_overrides[get_db_session] = _get_db_session_override

# Fixture de configuration de la base de données (SETUP/TEARDOWN)
@pytest.fixture(scope="session", autouse=True)
async def setup_database(override_get_db_session):
    """
    Crée et détruit la base de données de test et ses tables.
    """
    # SETUP: Création des tables dans la BDD de test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield # Exécute les tests

    # TEARDOWN: Suppression des tables après les tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Fixture pour l'event loop (requis par pytest-asyncio)
@pytest.fixture(scope="session")
def event_loop():
    """Régle l'event loop pour pytest-asyncio."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()