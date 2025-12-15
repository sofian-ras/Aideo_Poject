# aideo/backend/app/models/document_analysis.py

from pydantic import BaseModel, Field
from typing import List, Optional

# Modèle pour une date extraite
class DateDetail(BaseModel):
    date: str = Field(..., description="La date au format AAAA-MM-JJ.")
    description: str = Field(..., description="Description courte de ce que représente cette date (ex: 'Date limite de paiement').")

# Modèle pour un montant extrait
class AmountDetail(BaseModel):
    montant: float = Field(..., description="Le montant numérique (ex: 150.50).")
    description: str = Field(..., description="Description du montant (ex: 'Montant à payer' ou 'Remboursement').")

# Modèle de la réponse finale structurée par l'IA
class AIAnalysisResult(BaseModel):
    type: str = Field(..., description="Le type de document identifié (impôts, santé, assurance, etc.).")
    resume: str = Field(..., description="Résumé simple et clair en 2-3 phrases pour le citoyen.")
    actions: List[str] = Field(..., description="Liste des actions concrètes requises par ce document.")
    dates: List[DateDetail] = Field(..., description="Liste des dates importantes avec leur description.")
    montants: List[AmountDetail] = Field(..., description="Liste des montants clés trouvés.")
    raw_text: Optional[str] = Field(None, description="Le texte brut utilisé pour l'analyse (pour debug/vérification).")