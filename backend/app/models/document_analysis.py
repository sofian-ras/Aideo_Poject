from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any

# --- Pydantic Schemas pour la gestion des Documents ---

# 1. Modèle pour la réponse détaillée (inclut les données BDD + l'analyse IA)
class DocumentResponse(BaseModel):
    """Schéma de réponse complet d'un document (utilisé pour GET /documents/{id})."""
    id: int
    owner_id: str
    file_name: str
    content_type: str
    file_url: Optional[str] = None 
    
    # Données extraites par OCR/IA
    raw_text: Optional[str] = None
    ai_type: Optional[str] = None
    ai_resume: Optional[str] = None
    ai_actions: List[Any] = Field(default_factory=list)
    ai_dates: List[Any] = Field(default_factory=list)
    ai_montants: List[Any] = Field(default_factory=list)
    
    created_at: datetime
    
    class Config:
        from_attributes = True 


# 2. Modèle pour la création rapide 
class DocumentCreation(BaseModel):
    file_name: str
    content_type: str
    file_url: str
    raw_text: str
    owner_id: str
    
    class Config:
        from_attributes = True


# 3. Modèle pour la mise à jour (PATCH)
class DocumentUpdate(BaseModel):
    """Schéma de mise à jour (utilisé pour PATCH /documents/{id})."""
    file_name: Optional[str] = None
    ai_type: Optional[str] = None
    ai_resume: Optional[str] = None
    
    class Config:
        from_attributes = True