import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import uuid

# --- Configuration des variables d'environnement ---
STORAGE_ENDPOINT = os.getenv("STORAGE_ENDPOINT", "http://minio:9000")  # MinIO local
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "aideo_access_key")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "aideo_secret_key")
BUCKET_NAME = os.getenv("BUCKET_NAME", "aideo-documents")

# --- Initialisation du client S3 / MinIO ---
s3_client = boto3.client(
    's3',
    endpoint_url=STORAGE_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=boto3.session.Config(signature_version='s3v4'),
    verify=False  # IMPORTANT pour MinIO local sans HTTPS
)

# --- Vérification / création du bucket ---
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

# --- Upload de fichier ---
async def upload_file_to_s3(file_content: bytes, user_id: str, file_name: str) -> str:
    """
    Télécharge un fichier sur le stockage S3/MinIO.
    Retourne l'URL complète du fichier.
    """
    file_extension = os.path.splitext(file_name)[1]
    s3_key = f"documents/{user_id}/{str(uuid.uuid4())}{file_extension}"

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content
        )
        return f"{STORAGE_ENDPOINT}/{BUCKET_NAME}/{s3_key}"

    except NoCredentialsError:
        raise Exception("Les clés d'accès S3/MinIO sont manquantes ou invalides.")
    except Exception as e:
        print(f"Erreur d'upload S3/MinIO : {e}")
        raise Exception("Échec du téléchargement du fichier vers le stockage.")

# --- Création d'une URL pré-signée ---
def create_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Génère une URL pré-signée pour accéder temporairement au fichier."""
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

# --- Extraction de la clé S3 à partir de l'URL ---
def get_s3_key_from_url(file_url: str) -> str:
    """
    Transforme l'URL complète en clé S3.
    Exemple :
      URL : http://minio:9000/aideo-documents/documents/user_id/uuid.pdf
      Retour : documents/user_id/uuid.pdf
    """
    if not file_url:
        return None
    
    prefix = f"{STORAGE_ENDPOINT}/{BUCKET_NAME}/"
    if file_url.startswith(prefix):
        return file_url[len(prefix):]
    
    return None

# --- Suppression de fichier ---
async def delete_file_from_s3(file_url: str):
    """
    Supprime un fichier du stockage S3/MinIO à partir de son URL.
    """
    s3_key = get_s3_key_from_url(file_url)

    if not s3_key:
        print(f"Alerte: Clé S3 non valide pour suppression, URL: {file_url}")
        return

    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
        print(f"Fichier S3/MinIO supprimé : {s3_key}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"Alerte: Tentative de suppression d'une clé S3/MinIO inexistante : {s3_key}")
        else:
            print(f"Erreur critique lors de la suppression S3/MinIO : {e}")
            raise Exception("Échec de la suppression du fichier du stockage.")
    except Exception as e:
        print(f"Erreur inattendue lors de la suppression : {e}")
        raise Exception("Échec de la suppression du fichier du stockage.")
