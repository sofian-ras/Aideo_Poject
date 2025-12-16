# aideo/backend/app/main.py (VERSION CORRIGÉE)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.services.storage_service import check_bucket_existence 

# NOTE: Les imports des routeurs sont décalés APRÈS la définition de l'app.
# L'importation des modèles de base n'est plus nécessaire ici car elle se fait dans init_db ou les routeurs.

app = FastAPI(
    title="Aideo API - Assistance Documentaire",
    description="API pour le scan, l'analyse IA et la gestion des documents administratifs.",
    version="1.0.0",
)

# --- Configuration CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ÉVÉNEMENT DE DÉMARRAGE : Initialisation de la BDD et du Stockage ---

@app.on_event("startup")
async def startup_event():
    """Exécute l'initialisation de la BDD et vérifie le stockage S3/MinIO au démarrage de l'API."""
    
    # Importation des modèles de BDD juste avant init_db pour garantir leur chargement
    from app.models import base_models 
    
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


# --- INCLUSION DES ROUTEURS (Importation et inclusion à la fin) ---
from app.api import auth
from app.api import documents

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentification"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents & Scan"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)