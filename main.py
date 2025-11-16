from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Optional
import os
from dotenv import load_dotenv
import googlemaps  # para Google Places
from datetime import timedelta
import pandas as pd  # para big data / analise
from fastapi.security import OAuth2PasswordRequestForm

# importar modulos
from database import init_db
from models import UsuarioDocument, FavoritoDocument
from schemas import UsuarioCreate, UsuarioResponse, FavoritoCreate, FavoritoResponse
from auth import hash_password, verify_password, create_access_token, get_current_user

# CONFIGURAÇÃO INICIAL
load_dotenv()
app = FastAPI(title="Guia caruaru API")

# INICIALIZAÇÃO DO GOOGLE MAPS
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if GOOGLE_MAPS_API_KEY:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
else:
    gmaps = None
    print("⚠️ AVISO: API Key do Google Maps não encontrada. O servidor iniciou, mas a busca de locais não funcionará.")

CARUARU_LOCATION = (-8.28882, -35.9754)

# LOGICA DE STARTUP

@app.on_event("startup")
async def startup_ddb_client():
    """Conecta ao MongoDB antes de inicar o servidor."""
    await init_db()

# ENDPOINT AUTENTICAÇÃO

@app.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UsuarioCreate):
    """CADASTRO DO CLIENTE COM HASH DE SENHA"""
    if await UsuarioDocument.find_one(UsuarioDocument.email == user.email):
        raise HTTPException(status_code=400, detail="e-mail ja registrado.")

    # CRIPTOGRAFIA DA SENHA
    hashed_password = hash_password(user.senha)
    new_user = UsuarioDocument(
        email=user.email, nome=user.nome, senha=hashed_password)
    await new_user.insert()
    return new_user

@app.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """login e retorno do JWT"""
    user = await UsuarioDocument.find_one(UsuarioDocument.email == form_data.username)

    # verificar usuario e senha
    if not user or not verify_password(form_data.password, user.senha):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Usuario ou senha incorretos", headers={"www-Authenticate": "Bearer"},)

    # CRIA O TOKEN JWT

    access_token_expires = timedelta(minutes=float(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)))
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# endpoint publico(buscar fora)

@app.get("/search/place")
async def search_places(query: str,
                        type: str = "tourist_attraction",
                        radius: int = 5000,
                        min_rating: Optional[float] = None):
    """busca local no google places"""
    # (restaurantes, hospedagens, etc)
    try:
        results = gmaps.places_nearby(
            location=CARUARU_LOCATION,
            radius=radius,
            language='pt-BR',
            keyword=query,
            type=type,
        )
        places_list = results.get('results', [])

    except Exception as e:
        print(f"Erro no google Places:{e}")
        raise HTTPException(
            status_code=503, detail="Erro ao comunicar com api de terceiros.")

    # FILTRAGEM EM MEMORIA (PANDAS)
    if min_rating is not None and places_list:
        df = pd.DataFrame(places_list)

        # FILTRAGEM POR AVALIAÇÃO MINIMA
        df_filtrado = df[df['rating'].notna() & (df['rating'] >= min_rating)]
        places_list = df_filtrado.to_dict(orient='records')
        # converter de volta para json
    
    return places_list


# endpoints protegidos (monte seu guia / favoritos)

@app.post("/user/favorito", response_model=FavoritoResponse, status_code=status.HTTP_201_CREATED)
async def add_favorito(favorito_data: FavoritoCreate,
                       current_user: UsuarioDocument = Depends(get_current_user)):
    # exige login jwt
    """Adiciona um local como favorito do usuario logado"""
    new_favorito = FavoritoDocument(user_id=str(current_user.id),
                                    place_id_google=favorito_data.place_id_google, nome_local=favorito_data.nome_local)
    await new_favorito.insert()
    
    return new_favorito


@app.get("/user/favoritos", response_model=List[FavoritoResponse])
async def get_favoritos(current_user: UsuarioDocument = Depends(get_current_user)):
    """lista de todos os favoritos do usuario logado"""
    
    favoritos = await FavoritoDocument.find(FavoritoDocument.user_id == str(current_user.id)).to_list()
    
    return favoritos