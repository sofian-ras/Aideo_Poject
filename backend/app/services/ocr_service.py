# aideo/backend/app/services/ocr_service.py

import io
from PIL import Image
import pytesseract
from fastapi import HTTPException, status
from typing import Dict, Any

# Imports pour la BDD et le Stockage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.base_models import Document, User
from app.services.storage_service import upload_file_to_s3 


# --- OCR : Extraction du texte ---

async def perform_ocr(file_content: bytes, content_type: str) -> str:
    """
    Exécute l'OCR sur le contenu du fichier (image) en mémoire.
    """
    if content_type.startswith("image/"):
        try:
            image = Image.open(io.BytesIO(file_content))
            # Utilisation de 'fra' pour la langue française
            text = pytesseract.image_to_string(image, lang='fra') 
            return text
        except pytesseract.TesseractNotFoundError:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                 detail="Tesseract n'est pas installé ou trouvé sur le système.")
        except Exception as e:
            print(f"Erreur lors de l'OCR de l'image : {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                 detail="Erreur interne lors du traitement de l'image.")
    
    elif content_type == "application/pdf":
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, 
                            detail="La gestion des PDF n'est pas encore implémentée (nécessite pdf2image).")

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Type de fichier non supporté par le service OCR.")

# --- Gestion de l'Utilisateur Stub ---

async def create_stub_user_if_not_exists(user_id: str, db_session: AsyncSession):
    """Crée un utilisateur de test si celui-ci n'existe pas encore (pour l'MVP)."""
    # Recherche l'utilisateur
    result = await db_session.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        # Si l'utilisateur n'existe pas, on le crée
        new_user = User(
            id=user_id,
            email="test@aideo.com",
            hashed_password="hashed_password_stub" 
        )
        db_session.add(new_user)
        # Note : Le commit sera effectué par la fonction principale
        return new_user
    return user


# --- FONCTION PRINCIPALE APPELÉE PAR LE ROUTEUR ---

async def process_ocr_and_ai(
    file_content: bytes, 
    file_name: str, 
    content_type: str, 
    user_id: str,
    db_session: AsyncSession # NOUVEAU : Session BDD requise
) -> Dict[str, Any]:
    """
    Logique métier : Stockage, OCR, et préparation des données pour la BDD.
    """
    
    # 0. S'assurer que l'utilisateur existe (IMPORTANT pour la clé étrangère)
    await create_stub_user_if_not_exists(user_id, db_session)
    
    # 1. Upload vers le stockage (S3/MinIO)
    file_url = None
    try:
        # Appelle le service d'upload
        file_url = await upload_file_to_s3(file_content, user_id, file_name)
    except Exception as e:
        # Si l'upload échoue, on arrête
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Échec critique de l'upload du fichier vers le stockage: {e}")

    # 2. OCR : Extraction du texte brut
    raw_text = await perform_ocr(file_content, content_type)
    
    # 3. Validation de l'OCR
    if not raw_text.strip():
        # Devrait idéalement supprimer le fichier uploadé si l'OCR échoue
        return {
            "status": "fail",
            "message": "Le texte n'a pas pu être extrait correctement (OCR vide).",
        }
    
    # 4. Création de l'objet Document et Sauvegarde en BDD
    new_document = Document(
        owner_id=user_id,
        file_name=file_name,
        content_type=content_type,
        file_url=file_url, # Lien vers le fichier stocké
        raw_text=raw_text,
        # Les champs IA restent nuls pour cette phase
    )

    db_session.add(new_document)
    await db_session.commit()
    await db_session.refresh(new_document) # Pour obtenir l'ID généré
    
    # 5. Retour du succès
    return {
      "document_id": new_document.id,
      "status": "success",
      "message": "Document scanné, stocké et sauvegardé en base de données.",
    }