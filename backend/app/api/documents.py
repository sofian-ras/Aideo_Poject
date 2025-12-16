from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Path, Header
from app.services.ocr_service import process_ocr_and_ai 
from app.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List, Optional
from app.models.document_analysis import DocumentResponse, DocumentUpdate 
from app.models.base_models import Document, User 
from sqlalchemy.future import select
from pydantic import Field 

# Imports pour le stockage et la suppression de fichiers
from app.services.storage_service import create_presigned_url, delete_file_from_s3 

# Imports de Sécurité
from app.core.security import get_current_user_from_token 

# --- DÉPENDANCES ET TYPES (Les alias Annotated sont supprimés pour la fiabilité des tests) ---
# CurrentUser = Annotated[User, Depends(get_current_user_from_token)] 
# DB_Session = Annotated[AsyncSession, Depends(get_db_session)]
# ---------------------------

router = APIRouter()

# --- SCHÉMA DÉTAILLÉ DE RÉPONSE ---

class DetailedDocumentResponse(DocumentResponse):
    """Schéma étendu pour inclure le texte brut et l'URL de téléchargement."""
    raw_text: str = Field(..., description="Le texte brut extrait par l'OCR.")
    download_url: Optional[str] = Field(None, description="URL pré-signée sécurisée pour télécharger le fichier original (valable 1 heure).")


# -------------------------------------------------------------
# Route de Récupération de tous les documents (GET /)
# -------------------------------------------------------------

@router.get(
    "/", 
    response_model=List[DocumentResponse], 
    summary="Liste tous les documents de l'utilisateur"
)
async def list_user_documents(
    # Injection directe des dépendances pour la fiabilité (SOLUTION DU PROBLÈME)
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Récupère la liste de tous les documents scannés appartenant à l'utilisateur connecté.
    """
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

@router.get(
    "/{document_id}", 
    response_model=DetailedDocumentResponse, 
    summary="Récupère les détails complets d'un document"
)
async def get_document_details(
    document_id: Annotated[int, Path(description="L'ID entier du document à récupérer.")],
    # Injection directe des dépendances
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db_session)
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé. Ce document ne vous appartient pas.")

    # 3. Génération de l'URL de téléchargement sécurisée
    download_url = None
    if document.file_url:
        download_url = create_presigned_url(document.file_url)
    
    # 4. Conversion et ajout des champs supplémentaires pour la réponse détaillée
    response_data = DetailedDocumentResponse.model_validate(document)
    response_data.download_url = download_url
    
    return response_data

# -------------------------------------------------------------
# NOUVELLE ROUTE : Mise à Jour d'un document (PATCH /{document_id})
# -------------------------------------------------------------

@router.patch(
    "/{document_id}", 
    response_model=DocumentResponse, 
    summary="Met à jour les métadonnées d'un document"
)
async def update_document(
    document_id: Annotated[int, Path(description="L'ID entier du document à mettre à jour.")],
    update_data: DocumentUpdate, 
    # Injection directe des dépendances
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Met à jour les métadonnées du document spécifié (nom, résumé IA, etc.).
    """
    user_id = current_user.id
    
    # 1. Recherche du document
    result = await db.execute(
        select(Document)
        .filter(Document.id == document_id)
    )
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvé.")

    # 2. Vérification des droits d'accès
    if document.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé. Ce document ne vous appartient pas.")

    # 3. Préparation des données de mise à jour
    update_data_dict = update_data.model_dump(exclude_none=True)
    
    if not update_data_dict:
        return document 

    # 4. Mise à jour du modèle ORM
    for key, value in update_data_dict.items():
        setattr(document, key, value)
        
    # 5. Sauvegarde en BDD
    try:
        db.add(document)
        await db.commit()
        await db.refresh(document) 
    except Exception as e:
        print(f"Erreur de BDD lors de la mise à jour: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Échec de la mise à jour dans la base de données.")
    
    # 6. Retourne le document mis à jour
    return document


# -------------------------------------------------------------
# Route d'Upload (POST /scan)
# -------------------------------------------------------------

@router.post("/scan")
async def scan_document_upload(
    file: Annotated[UploadFile, File(description="Le fichier image ou PDF du document à analyser.")],
    # Injection directe des dépendances
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Route principale : Upload, Stockage, OCR et Sauvegarde du document.
    """
    if not file.content_type or not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seuls les fichiers images ou PDF sont acceptés.")

    file_content = await file.read()

    try:
        result = await process_ocr_and_ai(
            file_content=file_content,
            file_name=file.filename,
            content_type=file.content_type,
            user_id=current_user.id,
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

    return {
        "document_id": result.get("document_id"),
        "filename": file.filename,
        "status": result.get("status", "success"),
        "message": result.get("message", "Document traité et sauvegardé avec succès.")
    }


# -------------------------------------------------------------
# Route de Suppression d'un document (DELETE /{document_id})
# -------------------------------------------------------------

@router.delete(
    "/{document_id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    summary="Supprime un document et son fichier original du stockage"
)
async def delete_document(
    document_id: Annotated[int, Path(description="L'ID entier du document à supprimer.")],
    # Injection directe des dépendances
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Supprime un document de la base de données et son fichier associé de MinIO/S3.
    """
    user_id = current_user.id
    
    # 1. Recherche du document
    result = await db.execute(
        select(Document)
        .filter(Document.id == document_id)
    )
    document = result.scalars().first()
    
    if not document:
        return # 204 No Content

    # 2. Vérification des droits d'accès
    if document.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé. Ce document ne vous appartient pas.")

    # 3. Suppression du fichier physique de MinIO/S3
    if document.file_url:
        try:
            await delete_file_from_s3(document.file_url)
        except Exception as e:
            print(f"Erreur (non critique) lors de la suppression MinIO pour doc ID {document_id}: {e}")

    # 4. Suppression de l'enregistrement BDD
    try:
        await db.delete(document)
        await db.commit()
    except Exception as e:
        print(f"Erreur de BDD lors de la suppression: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Échec de la suppression dans la base de données.")
    
    return