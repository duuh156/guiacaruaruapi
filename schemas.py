# schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, conint, Field
from beanie import PydanticObjectId
from typing import Optional, Annotated
from pydantic import conint 
from datetime import datetime

# 1 autenticaçao 

class UsuarioCreate(BaseModel):
    email: EmailStr
    nome: str
    senha: str 

class UsuarioResponse(BaseModel):
    id: PydanticObjectId
    email: EmailStr
    nome: str

class Config: 
    populate_by_name = True

# 2 favoritos

class FavoritoCreate(BaseModel):
    place_id_google: str
    nome_local: str

class FavoritoResponse(FavoritoCreate):
    model_config = ConfigDict(from_attributes=True,populate_by_name=True)
    id: PydanticObjectId
    user_id: str

# AVALIAÇÃO
class AvaliacaoCreate(BaseModel):
    place_id_google: str 
    nota: Annotated[int,Field(ge=1, le=5)]
    comentario: Optional[str] = None
    
class AvaliacaoResponse(AvaliacaoCreate):
    model_config = ConfigDict(populate_by_name=True)
    id:PydanticObjectId
    user_id:str

class EventoCreate(BaseModel):
    nome: str
    data_inicio: str
    local: str
    descricao: Optional[str] = "Sem descrição"
    preco: float = 0.0
    imagem_url: Optional[str] = None

class EventoResponse(EventoCreate):
    id: PydanticObjectId