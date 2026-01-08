from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Path
from typing import Annotated, List, Optional
from pydantic import Field
from sqlalchemy.future import select

from app.services.ocr_service import process_ocr_and_ai
from app.services.storage_service import create_presigned_url, delete_file_from_s3
from app.core.security import get_current_user_from_token
from app.dependencies import DB_SESSION_DEPENDENCY

from app.models.document_analysis import DocumentResponse, DocumentUpdate
from app.models.base_models import Document

router = APIRouter()


# -------------------------------------------------------------
# Schéma de réponse détaillé
# -------------------------------------------------------------

class DetailedDocumentResponse(DocumentResponse):
    raw_text: str = Field(..., description="Texte brut extrait par l'OCR")
    download_url: Optional[str] = Field(None, description="URL pré-signée (1h)")


# -------------------------------------------------------------
# GET /documents/
# -------------------------------------------------------------

@router.get(
    "/",
    response_model=List[DocumentResponse],
    summary="Liste tous les documents de l'utilisateur",
)
async def list_user_documents(
 #   current_user=Depends(get_current_user_from_token),
    db=DB_SESSION_DEPENDENCY,
):
    user_id = 1  # Pour l'instant, on utilise un user_id fixe pour les tests

    try:
        result = await db.execute(
            select(Document)
            .filter(Document.owner_id == user_id)
            .order_by(Document.created_at.desc())
        )
        documents = result.scalars().all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des documents",
        )

    return documents


# -------------------------------------------------------------
# GET /documents/{document_id}
# -------------------------------------------------------------

@router.get(
    "/{document_id}",
    response_model=DetailedDocumentResponse,
    summary="Détails complets d'un document",
)
async def get_document_details(
    document_id: Annotated[int, Path(...)],
    current_user=Depends(get_current_user_from_token),
    db=DB_SESSION_DEPENDENCY,
):
    result = await db.execute(select(Document).filter(Document.id == document_id))
    document = result.scalars().first()

    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    download_url = None
    if document.file_url:
        download_url = create_presigned_url(document.file_url)

    response = DetailedDocumentResponse.model_validate(document)
    response.download_url = download_url

    return response


# -------------------------------------------------------------
# PATCH /documents/{document_id}
# -------------------------------------------------------------

@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Mise à jour d'un document",
)
async def update_document(
    document_id: Annotated[int, Path(...)],
    update_data: DocumentUpdate,
    current_user=Depends(get_current_user_from_token),
    db=DB_SESSION_DEPENDENCY,
):
    result = await db.execute(select(Document).filter(Document.id == document_id))
    document = result.scalars().first()

    if not document:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    data = update_data.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(document, key, value)

    try:
        await db.commit()
        await db.refresh(document)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erreur de mise à jour")

    return document


# -------------------------------------------------------------
# POST /documents/scan
# -------------------------------------------------------------

@router.post("/scan", summary="Upload + OCR + IA")
async def scan_document_upload(
    file: Annotated[UploadFile, File(...)],
    # current_user=Depends(get_current_user_from_token),
    db=DB_SESSION_DEPENDENCY,
):
    user_id = 1  # Pour l'instant, on utilise un user_id fixe pour les tests
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Type de fichier invalide")

    content = await file.read()

    result = await process_ocr_and_ai(
        file_content=content,
        file_name=file.filename,
        content_type=file.content_type,
        user_id= user_id, # À remplacer par current_user.id quand l'auth sera en place
        db_session=db,
    )

    return result


# -------------------------------------------------------------
# DELETE /documents/{document_id}
# -------------------------------------------------------------

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Suppression d'un document",
)
async def delete_document(
    document_id: Annotated[int, Path(...)],
    current_user=Depends(get_current_user_from_token),
    db=DB_SESSION_DEPENDENCY,
):
    result = await db.execute(select(Document).filter(Document.id == document_id))
    document = result.scalars().first()

    if not document:
        return

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    if document.file_url:
        await delete_file_from_s3(document.file_url)

    await db.delete(document)
    await db.commit()