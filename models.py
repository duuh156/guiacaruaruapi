from beanie import Document
from pydantic import Field 

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
