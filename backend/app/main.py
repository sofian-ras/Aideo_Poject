# aideo/backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents 
from app.core.database import init_db
from app.models import base_models # Nécessaire pour que SQLAlchemy trouve les modèles lors de l'init_db
from app.services.storage_service import check_bucket_existence # Importation du service de vérification MinIO/S3

# Nous allons inclure les routeurs spécifiques une fois qu'ils seront créés
# from app.api import auth # Laissez cette ligne pour l'authentification future

app = FastAPI(
    title="Aideo API - Assistance Documentaire",
    description="API pour le scan, l'analyse IA et la gestion des documents administratifs.",
    version="1.0.0",
)

# --- Configuration CORS (Obligatoire pour le développement mobile/web) ---
# En production, il faudrait restreindre 'allow_origins' aux domaines de l'application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Temporairement autorisé pour le développement local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ÉVÉNEMENT DE DÉMARRAGE : Initialisation de la BDD et du Stockage ---

@app.on_event("startup")
async def startup_event():
    """Exécute l'initialisation de la BDD et vérifie le stockage S3/MinIO au démarrage de l'API."""
    print("Tentative d'initialisation de la base de données...")
    await init_db()
    
    print("Vérification et création du bucket de stockage MinIO/S3...")
    await check_bucket_existence()
    
    print("Services backend Aideo prêts.")


# --- Routes de base ---

@app.get("/")
def read_root():
    """Route de santé : Vérifie que l'API est fonctionnelle."""
    return {"message": "Bienvenue sur l'API Aideo. Le service est opérationnel."}

# Inclure les routeurs des fonctionnalités
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents & Scan"])
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentification"]) # À décommenter plus tard

if __name__ == "__main__":
    import uvicorn
    # Lance le serveur Uvicorn si le fichier est exécuté directement
    uvicorn.run(app, host="0.0.0.0", port=8000)