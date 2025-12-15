# aideo/backend/app/services/ai_service.py

import os
import json
from openai import AsyncOpenAI
from app.models.base_models import Document, User # Les modèles de BDD
from fastapi import HTTPException
from typing import Dict, Any

# Initialisation du client OpenAI (doit être configuré via variables d'environnement)
# client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Le prompt système pour guider le modèle
SYSTEM_PROMPT = """Tu es un assistant expert qui aide les citoyens à comprendre et gérer leurs documents administratifs en français. Ta tâche est d'analyser le texte brut fourni et d'en extraire les informations clés dans une structure JSON stricte.

Règles à respecter :
1. Analyse le contexte pour identifier le type de document (impôts, santé, CAF, assurance, banque, etc.).
2. Fournis un résumé en 2-3 phrases maximales et extrêmement simples (langage non-administratif).
3. Liste les actions concrètes requises. Si aucune action n'est requise, la liste doit être vide.
4. Extrais toutes les dates importantes (limites, rendez-vous, etc.) au format AAAA-MM-JJ.
5. Extrais tous les montants financiers mentionnés.
6. La réponse DOIT être un objet JSON valide, conforme au schéma fourni (Response Model)."""


async def analyze_document_with_ai(document_text: str) -> Dict[str, Any]:
    """
    Appelle l'API d'IA pour structurer le texte brut d'un document.
    """

    # 1. Le prompt utilisateur basé sur le contenu OCR
    user_prompt = f"Document reçu :\n---\n{document_text}\n---"

    # --- SIMULATION (Retirer ce bloc pour le déploiement réel) ---
    if os.getenv("ENV") != "production":
        # Simule une réponse pour ne pas dépendre de l'API pendant les tests locaux
        simulated_data = {
            "type": "Facture d'Électricité (Simulé)",
            "resume": "Ce document vous informe que votre facture d'électricité de 125.50 € est due. La date limite pour le paiement est le 2026-02-28.",
            "actions": ["Vérifier la consommation", "Payer le montant de 125.50 €"],
            "dates": [{"date": "2026-02-28", "description": "Date limite de paiement"}],
            "montants": [{"montant": 125.50, "description": "Montant total de la facture"}]
        }
        # Valide le modèle pour s'assurer qu'il respecte le schéma
        return AIAnalysisResult(**simulated_data).model_dump()
    # --- FIN SIMULATION ---


    # --- APPEL RÉEL À L'API D'IA (Utiliser ce bloc en production) ---
    """
    try:
        # Utilisation de la fonctionnalité de réponse JSON Structurée d'OpenAI/Anthropic
        response = await client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",  # Ou claude-3-sonnet/opus
            response_model=AIAnalysisResult, # Exige que la réponse respecte notre schéma Pydantic
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
        )

        # La réponse est directement un objet Pydantic valide
        return response.choices[0].message.content.model_dump()

    except Exception as e:
        print(f"Erreur lors de l'appel à l'API IA : {e}")
        # En cas d'échec de l'IA (timeout, erreur de parsage), nous levons une exception
        raise HTTPException(status_code=500, detail="L'analyse du document par l'IA a échoué.")
    """
    # --- FIN APPEL RÉEL ---