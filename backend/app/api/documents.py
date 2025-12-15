# aideo/backend/app/api/documents.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from app.services.ocr_service import process_ocr_and_ai # Importation future
# from app.core.security import get_current_user # Importation future pour l'authentification
from typing import Annotated

# aideo/backend/app/api/documents.py (Ajustement du retour)

# ... (imports inchangés) ...

@router.post("/scan")
async def scan_document_upload(
    file: Annotated[UploadFile, File(description="Le fichier image ou PDF du document à analyser.")],
    # current_user: CurrentUser
):
    # ... (Validation et lecture du fichier inchangés) ...

    # 3. Appel du service d'OCR (maintenant sans IA)
    try:
        # analysis_result contient maintenant raw_text et les champs structurés nuls.
        analysis_result = await process_ocr_and_ai(
            file_content=file_content,
            file_name=file.filename,
            content_type=file.content_type,
            # user_id=current_user.get("user_id")
        )
        
    except Exception as e:
        # ... (Gestion des erreurs inchangée) ...
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec du traitement du document par le service OCR.",
        )


    # 4. Retour du résultat
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "status": analysis_result.get("status", "success"),
        "raw_text_extracted": analysis_result.get("raw_text"), # Montrer le texte brut
        "message": analysis_result.get("message", "Traitement initial terminé.")
    }