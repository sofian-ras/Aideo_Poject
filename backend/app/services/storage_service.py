import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import uuid
from datetime import timedelta

# Configuration des variables d'environnement (utilisées par MinIO ou S3)
# Si vous utilisez MinIO via Docker Compose, ajustez l'ENDPOINT_URL.
STORAGE_ENDPOINT = os.getenv("STORAGE_ENDPOINT", "http://localhost:9000") # MinIO par défaut
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "aideo_access_key")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "aideo_secret_key")
BUCKET_NAME = os.getenv("BUCKET_NAME", "aideo-documents")

# Initialisation du client S3 (utilisé pour MinIO ou S3 réel)
# use_ssl=False est souvent nécessaire pour MinIO en développement local
s3_client = boto3.client(
    's3',
    endpoint_url=STORAGE_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=boto3.session.Config(signature_version='s3v4'),
    verify=False # IMPORTANT pour MinIO local (si pas de HTTPS)
)

async def check_bucket_existence():
    """Vérifie l'existence du bucket et le crée s'il n'existe pas."""
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' existe déjà.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"Bucket '{BUCKET_NAME}' non trouvé. Création en cours...")
            s3_client.create_bucket(Bucket=BUCKET_NAME)
            print(f"Bucket '{BUCKET_NAME}' créé avec succès.")
        else:
            raise e


async def upload_file_to_s3(file_content: bytes, user_id: str, file_name: str) -> str:
    """
    Télécharge le contenu binaire d'un fichier vers le stockage d'objets.

    Retourne : l'URL de la clé S3 du fichier.
    """
    # Clé du fichier : format standard pour une bonne organisation S3
    # Ex: documents/893c834a-9b4f-4d2a-a9e3-82d22b67e00e/2025/mon-fichier-uuid.pdf
    file_extension = os.path.splitext(file_name)[1]
    s3_key = f"documents/{user_id}/{str(uuid.uuid4())}{file_extension}"

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            # Le type de contenu est défini par défaut, peut être passé en paramètre
        )
        # Retourne le chemin complet pour le stockage en BDD
        return f"{STORAGE_ENDPOINT}/{BUCKET_NAME}/{s3_key}"

    except NoCredentialsError:
        raise Exception("Les clés d'accès S3/MinIO sont manquantes ou invalides.")
    except Exception as e:
        print(f"Erreur d'upload S3/MinIO : {e}")
        raise Exception("Échec du téléchargement du fichier vers le stockage.")

# Fonction pour créer un lien temporaire pour le téléchargement sécurisé
def create_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Génère une URL pré-signée pour un accès temporaire et sécurisé."""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"Erreur de création d'URL pré-signée : {e}")
        return None