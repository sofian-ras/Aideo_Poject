# aideo/backend/app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# NOTE : En environnement de production/développement, cette URL doit venir des variables d'environnement
# Nous utilisons ici une valeur par défaut pour le développement local.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/aideo_db"
)

# 1. Création du moteur de connexion asynchrone
# echo=True pour afficher les requêtes SQL générées (utile pour le debug)
engine = create_async_engine(DATABASE_URL, echo=True)

# 2. Définition de la base pour les modèles
# Toutes les classes de modèles ORM hériteront de cette Base.
Base = declarative_base()

# 3. Création du générateur de sessions asynchrones
# expire_on_commit=False pour éviter de charger/décharger des objets après un commit
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

# 5. Fonction pour créer toutes les tables (à appeler au démarrage/setup)
async def init_db():
    """Crée toutes les tables définies par les modèles."""
    async with engine.begin() as conn:
        # Permet à SQLAlchemy de créer les tables si elles n'existent pas
        await conn.run_sync(Base.metadata.create_all)