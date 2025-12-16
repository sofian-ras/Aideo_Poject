from .base import Base # Importation corrigée
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
import uuid

# --- 1. Modèle Utilisateur ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    documents = relationship("Document", back_populates="owner")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


# --- 2. Modèle Document ---

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    
    owner_id = Column(String, ForeignKey("users.id")) 
    
    file_name = Column(String)
    content_type = Column(String)
    file_url = Column(String, nullable=True) 
    
    raw_text = Column(Text) 
    
    ai_type = Column(String, nullable=True)      
    ai_resume = Column(Text, nullable=True)      
    ai_actions = Column(JSON, default=[])        
    ai_dates = Column(JSON, default=[])          
    ai_montants = Column(JSON, default=[])       
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(id={self.id}, name='{self.file_name}')>"