import io
from PIL import Image
import pytesseract
from fastapi import HTTPException, status
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.base_models import Document, User
from app.services.storage_service import upload_file_to_s3
from app.services.ai_service import analyze_document_with_ai
import os
import pytesseract

# Si on est dans Docker (Linux), le chemin est /usr/bin/tesseract
# Sinon, on garde ton chemin Windows pour tes tests locaux hors Docker
if os.name == 'nt':  # 'nt' veut dire Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Sinon, on est sur Linux/Docker
    pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

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
    db_session: AsyncSession
) -> Dict[str, Any]:
    
    # 0. S'assurer que l'utilisateur existe
    await create_stub_user_if_not_exists(user_id, db_session)
    
    # 1. Upload vers MinIO
    try:
        file_url = await upload_file_to_s3(file_content, user_id, file_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur stockage: {e}")

    # 2. OCR : Extraction du texte brut
    raw_text = await perform_ocr(file_content, content_type)
    
    # 3. Validation de l'OCR
    if not raw_text.strip():
        return {"status": "fail", "message": "OCR vide."}

    # --- NOUVEAU : APPEL À L'IA (OLLAMA) ---
    ai_data = await analyze_document_with_ai(raw_text)
    if not ai_data:
        ai_data = {} # Évite les erreurs si l'IA échoue
    # ---------------------------------------
    
    # 4. Création de l'objet Document avec les données de l'IA
    new_document = Document(
        owner_id=user_id,
        file_name=file_name,
        content_type=content_type,
        file_url=file_url,
        raw_text=raw_text,
        # On injecte ici les résultats de l'IA locale
        ai_type=ai_data.get("type"),
        ai_resume=ai_data.get("resume"),
        ai_actions=ai_data.get("actions", []),
        ai_dates=ai_data.get("dates", []),
        ai_montants=ai_data.get("montants", [])
    )

    db_session.add(new_document)
    await db_session.commit()
    await db_session.refresh(new_document)
    
    return {
      "document_id": new_document.id,
      "status": "success",
      "message": "Document scanné et analysé par l'IA avec succès.",
    }