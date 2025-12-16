from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from app.models.base import Base
# NOTE : Les valeurs par défaut sont ici pour le cas où .env ou Docker Compose ne fonctionnent pas
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@db:5432/aideo_db" # Utilisation de 'db' pour l'interne Docker
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/aideo_test_db" # Base de données de test
)

# Détermine l'URL à utiliser (Logique critique pour les tests unitaires)
if os.environ.get("TESTING") == "True":
    ASYNC_DATABASE_URL = TEST_DATABASE_URL
else:
    ASYNC_DATABASE_URL = DATABASE_URL
    
# 1. Création du moteur de connexion asynchrone
# Utilisation de ASYNC_DATABASE_URL pour se connecter soit à la BDD de prod, soit à celle de test.
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)

# 2. Suppression de la ligne incorrecte : Base = declarative_base() 
# La classe Base est importée depuis base_models.py, elle ne doit pas être redéfinie ici.

# 3. Création du générateur de sessions asynchrones
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 4. Fonction utilitaire pour obtenir une session (Dépendance FastAPI)
async def get_db_session():
    """Fournit une session de base de données asynchrone pour FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session

# 5. Fonction pour créer toutes les tables
async def init_db():
    """Crée toutes les tables définies par les modèles."""
    async with engine.begin() as conn:
        # Utilise la Base importée pour créer les tables
        await conn.run_sync(Base.metadata.create_all)