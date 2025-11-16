# schemas.py
from pydantic import BaseModel, EmailStr
from beanie import PydanticObjectId
from typing import Optional

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
    id: PydanticObjectId
    user_id: str

    class Config: 
        populate_by_name = True