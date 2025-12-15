#  Aideo : Assistant Documentaire AI (MVP)

Bienvenue sur le projet Aideo. Cette API FastAPI sert de cœur à un assistant documentaire, gérant l'authentification, le stockage sécurisé, l'OCR et le CRUD complet des documents.

##  Stack Technique

* API Web: FastAPI (Python)
* Base de Données: PostgreSQL (SQLAlchemy Async)
* Stockage d'Objets: MinIO (Compatible S3)
* OCR: Tesseract (via PyTesseract)
* Authentification: JWT (JSON Web Tokens)
* Conteneurisation: Docker & Docker Compose

##  Architecture du Projet

Le projet est structuré comme suit :

aideo/
├── backend/
│   ├── app/
│   │   ├── api/          # Routeurs (auth.py, documents.py)
│   │   ├── core/         # Configuration (database.py, security.py)
│   │   ├── models/       # Modèles BDD et Pydantic
│   │   ├── services/     # Logique métier (ocr_service.py, storage_service.py)
│   │   └── main.py       # Point d'entrée FastAPI
│   ├── requirements.txt
│   └── tests/            # Tests unitaires
├── .env                  # Variables d'environnement locales
└── docker-compose.yml

##  Installation et Démarrage

### 1. Prérequis

* Docker
* Docker Compose

### 2. Configuration des Variables d'Environnement

Créez le fichier **.env** à la racine (aideo/.env) :

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aideo_db

S3_ACCESS_KEY=aideo_minio_user
S3_SECRET_KEY=aideo_minio_password
STORAGE_ENDPOINT=http://minio:9000
BUCKET_NAME=aideo-documents
STORAGE_REGION=eu-west-1

JWT_SECRET_KEY=CLE_SECRETE_TRES_COMPLEXE_A_REMPLACER_EN_PROD
ACCESS_TOKEN_EXPIRE_MINUTES=60

### 3. Lancement des Services

Lancez tous les services conteneurisés :

# À la racine du projet (dossier aideo/)
docker-compose up --build -d

| Service | Accès Local | Note |
| :--- | :--- | :--- |
| API Backend | http://localhost:8000 | Documentation sur /docs |
| MinIO Console| http://localhost:9001 | Interface de gestion des fichiers |

---

##  Workflow d'Authentification

Toutes les routes de documents nécessitent l'en-tête Authorization: Bearer <token>.

1.  Inscription: POST /api/v1/auth/register
2.  Connexion: POST /api/v1/auth/login -> Récupération du **JWT Token** (access_token).

##  Exécution des Tests

Pour valider le code, utilisez pytest à l'intérieur du conteneur API (nécessite le lancement via docker-compose up au préalable) :

1.  Accédez au conteneur de l'API :
    docker exec -it aideo-api bash
2.  Lancez Pytest :
    pytest

---