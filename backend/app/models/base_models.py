from .base import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
import uuid

# --- 1. Modèle Utilisateur ---
class User(Base):
    __tablename__ = "users"
    
    # ID généré par l'application (plus portable que l'ID séquentiel de la BDD)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation : un utilisateur peut avoir plusieurs documents
    documents = relationship("Document", back_populates="owner")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


# --- 2. Modèle Document ---
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Clé étrangère vers l'utilisateur (un document appartient à un seul utilisateur)
    owner_id = Column(String, ForeignKey("users.id")) 
    
    # Détails du fichier
    file_name = Column(String)
    content_type = Column(String)
    # URL vers le stockage sécurisé (MinIO/S3), stocké ici pour la référence
    file_url = Column(String, nullable=True) 
    
    # Données extraites par l'OCR et l'IA
    raw_text = Column(Text) # Le texte brut de l'OCR
    
    # Les champs structurés de l'IA (stockés en JSON pour la flexibilité)
    ai_type = Column(String, nullable=True)     # Ex: "Facture", "Impôts"
    ai_resume = Column(Text, nullable=True)     # Résumé IA
    ai_actions = Column(JSON, default=[])       # Liste des actions
    ai_dates = Column(JSON, default=[])         # Liste des dates structurées
    ai_montants = Column(JSON, default=[])      # Liste des montants structurés
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation inverse pour accéder à l'utilisateur
    owner = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(id={self.id}, name='{self.file_name}')>"