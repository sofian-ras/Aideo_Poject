import json
import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException

# Configuration via variables d'environnement (définies dans docker-compose)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
AI_MODEL = os.getenv("AI_MODEL", "mistral")

SYSTEM_PROMPT = """Tu es un assistant expert qui aide les citoyens à comprendre leurs documents administratifs. 
Analyse le texte brut fourni et extrais les informations dans une structure JSON stricte.
Règles :
1. Identifie le type (impôts, santé, facture, etc.).
2. Résumé simple en 2 phrases.
3. Liste les actions concrètes.
4. Dates importantes au format AAAA-MM-JJ.
5. Montants financiers trouvés.
Réponds UNIQUEMENT avec le JSON."""

async def analyze_document_with_ai(document_text: str) -> Dict[str, Any]:
    """
    Appelle l'IA locale (Ollama) pour analyser le texte du document.
    """
    
    # Préparation de la requête pour Ollama
    # Note : On combine le system prompt et le texte pour Mistral
    full_prompt = f"{SYSTEM_PROMPT}\n\nDocument à analyser :\n{document_text}"
    
    payload = {
        "model": AI_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "num_predict": 200,  # Limite la longueur de la réponse pour gagner du temps
            "temperature": 0     # Rend l'IA plus rapide et plus précise
        }
    }

    try:
        # Augmentation du timeout car l'IA locale peut être lente (30 à 60s selon ton PC)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            response.raise_for_status()
            
            raw_response = response.json()
            # La réponse d'Ollama contient le texte généré dans le champ 'response'
            ai_content = raw_response.get("response")
            
            # Conversion de la chaîne de caractères JSON en dictionnaire Python
            return json.loads(ai_content)

    except httpx.TimeoutException:
        print("L'IA a mis trop de temps à répondre.")
        return _get_fallback_data()
    except Exception as e:
        print(f"Erreur lors de l'appel à Ollama : {e}")
        return _get_fallback_data()

def _get_fallback_data() -> Dict[str, Any]:
    """Retourne une structure vide en cas d'erreur de l'IA pour ne pas bloquer le scan."""
    return {
        "type": "Inconnu",
        "resume": "L'analyse automatique n'a pas pu être effectuée.",
        "actions": [],
        "dates": [],
        "montants": []
    }