# aideo/backend/app/api/documents.py (Mise à jour pour l'authentification JWT)

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Path, Header
from app.services.ocr_service import process_ocr_and_ai 
from app.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List, Optional
from app.models.document_analysis import DocumentResponse 
from app.models.base_models import Document, User # Import de User pour la dépendance
from sqlalchemy.future import select
from pydantic import Field # Nécessaire pour DetailedDocumentResponse

# Imports pour le stockage
from app.services.storage_service import create_presigned_url 

# Imports de Sécurité
from app.core.security import get_current_user_from_token # NOUVELLE DÉPENDANCE

# --- DÉPENDANCES ET TYPES MIS À JOUR ---
# L'utilisateur actuel est maintenant l'objet User SQLAlchemy, récupéré par JWT
CurrentUser = Annotated[User, Depends(get_current_user_from_token)] 
DB_Session = Annotated[AsyncSession, Depends(get_db_session)]
# ----------------------------------------

router = APIRouter()

# -------------------------------------------------------------
# Route de Récupération de tous les documents (GET /)
# -------------------------------------------------------------

@router.get(
    "/", 
    response_model=List[DocumentResponse], 
    summary="Liste tous les documents de l'utilisateur"
)
async def list_user_documents(
    current_user: CurrentUser, # Utilisateur authentifié requis
    db: DB_Session
):
    """
    Récupère la liste de tous les documents scannés appartenant à l'utilisateur connecté.
    """
    # L'ID de l'utilisateur est accessible directement via l'objet User
    user_id = current_user.id
    
    try:
        result = await db.execute(
            select(Document)
            .filter(Document.owner_id == user_id)
            .order_by(Document.created_at.desc())
        )
        documents = result.scalars().all()
        
    except Exception as e:
        print(f"Erreur de récupération des documents : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la récupération des documents depuis la base de données.",
        )
        
    return documents

# -------------------------------------------------------------
# Route : Récupération d'un document spécifique (GET /{document_id})
# -------------------------------------------------------------

class DetailedDocumentResponse(DocumentResponse):
    """Schéma étendu pour inclure le texte brut et l'URL de téléchargement."""
    raw_text: str = Field(..., description="Le texte brut extrait par l'OCR.")
    download_url: Optional[str] = Field(None, description="URL pré-signée sécurisée pour télécharger le fichier original (valable 1 heure).")


@router.get(
    "/{document_id}", 
    response_model=DetailedDocumentResponse, 
    summary="Récupère les détails complets d'un document"
)
async def get_document_details(
    document_id: Annotated[int, Path(description="L'ID entier du document à récupérer.")],
    current_user: CurrentUser, # Utilisateur authentifié requis
    db: DB_Session
):
    """
    Récupère un document spécifique, vérifie les droits et génère un lien de téléchargement.
    """
    user_id = current_user.id
    
    # 1. Recherche du document en BDD
    result = await db.execute(
        select(Document)
        .filter(Document.id == document_id)
    )
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvé.")
    
    # 2. Vérification des droits d'accès
    if document.owner_id != user_id:
        # L'utilisateur ne peut accéder qu'à ses propres documents
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé. Ce document ne vous appartient pas.")

    # 3. Génération de l'URL de téléchargement sécurisée
    download_url = None
    if document.file_url:
        download_url = create_presigned_url(document.file_url)
    
    # 4. Conversion et ajout des champs supplémentaires pour la réponse détaillée
    # On utilise le DocumentResponse comme base
    response_data = DetailedDocumentResponse.model_validate(document)
    response_data.download_url = download_url
    
    return response_data

# -------------------------------------------------------------
# Route d'Upload (POST /scan)
# -------------------------------------------------------------

@router.post("/scan")
async def scan_document_upload(
    file: Annotated[UploadFile, File(description="Le fichier image ou PDF du document à analyser.")],
    current_user: CurrentUser, # Utilisateur authentifié requis
    db: DB_Session
):
    """
    Route principale : Upload, Stockage, OCR et Sauvegarde du document.
    """
    # Validation basique du type de fichier (à améliorer)
    if not file.content_type or not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seuls les fichiers images ou PDF sont acceptés.")

    # Lecture du contenu du fichier
    file_content = await file.read()

    # Appel du service d'OCR et de Sauvegarde
    try:
        result = await process_ocr_and_ai(
            file_content=file_content,
            file_name=file.filename,
            content_type=file.content_type,
            user_id=current_user.id, # Utilisation de l'ID utilisateur réel
            db_session=db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur de traitement (OCR/Sauvegarde) : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec du traitement ou de la sauvegarde du document: {e}",
        )

    # Retour du résultat
    return {
        "document_id": result.get("document_id"),
        "filename": file.filename,
        "status": result.get("status", "success"),
        "message": result.get("message", "Document traité et sauvegardé avec succès.")
    }