from beanie import Document
from pydantic import Field 
from typing import Optional
from datetime import datetime


# 1. MODELO DE USUARIO 
class UsuarioDocument(Document):
    email: str = Field(unique=True, index=True)
    nome: str
    senha_hash: str #senha criptografia (segurança)

    class Settings:
        name = "usuarios"
# 2. MODELO DE FAVORITO
class FavoritoDocument(Document):
    user_ir: str
    place_id_google: str
    nome_local: str
    
    class Settings: 
        name = "favoritos"
# 3. MODELO DE AVALIAÇÃO
class AvaliacaoDocument(Document):
    user_id: str
    place_id_google: str 
    nota: int = Field(ge=1, le=5)
    comentario: Optional[str] = None 
    data_criacao: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name= "avaliacoes"
        indexes = ["place_id_google"]