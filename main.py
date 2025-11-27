from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Optional
import os
from dotenv import load_dotenv
import googlemaps  # para Google Places
from datetime import timedelta
import pandas as pd  # para big data / analise
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# importar modulos
from database import init_db
from models import UsuarioDocument, FavoritoDocument, AvaliacaoDocument, EventoDocument
from schemas import UsuarioCreate, UsuarioResponse, FavoritoCreate, FavoritoResponse, AvaliacaoCreate, AvaliacaoResponse, EventoCreate, EventoResponse
from auth import hash_password, verify_password, create_access_token, get_current_user

# CONFIGURAÇÃO INICIAL
load_dotenv()

# INICIALIZAÇÃO DO GOOGLE MAPS

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") 

if GOOGLE_MAPS_API_KEY:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
else: 
    gmaps = None
    print("⚠️ AVISO: API Key do Google Maps não encontrada.")

CARUARU_LOCATION = (-8.28882, -35.9754)

# LOGICA DE STARTUP (Ligar Banco de Dados)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando conexão com o banco de dados...")
    await init_db() 
    yield 
    print("Servidor desligado")

app = FastAPI(title="Guia Caruaru API", lifespan=lifespan)

# CONFIGURAÇÃO DO CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

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

#  AVALIAÇÃO 
@app.post("/avaliacoes", response_model=AvaliacaoResponse,status_code=status.HTTP_201_CREATED)
async def criar_avaliacao(
    avaliacao_data: AvaliacaoCreate,
    current_user: UsuarioDocument = Depends(get_current_user)):

    nova_avaliacao = AvaliacaoDocument (
     user_id=str(current_user.id), 
        place_id_google=avaliacao_data.place_id_google,
        nota=avaliacao_data.nota,
        comentario=avaliacao_data.comentario)

    await nova_avaliacao.insert()
    return nova_avaliacao

@app.get("/avaliacoes/{place_id_google}",response_model=List[AvaliacaoResponse])
async def get_avaliacoes_por_local(place_id_google: str):
    avaliacoes = await AvaliacaoDocument.find(AvaliacaoDocument.place_id_google ==place_id_google).to_list()
    return avaliacoes

# CALCULAR A MEDIA DA NOTA 
@app.get("/avaliacoes/media/{place_id_google}")
async def get_media_avaliacoes(place_id_google:str):
    
    avaliacoes = await AvaliacaoDocument.find(AvaliacaoDocument.place_id_google == place_id_google).to_list()
    
    if not avaliacoes:
        return{"place_id": place_id_google,"media":0,"total_avaliacoes":0}
    
    df = pd.DataFrame([vars(a)for a in avaliacoes])
    media = df['nota'].mean()

    return{ 
       "place_id":place_id_google,
       "media": round(media,1),
       "total_avaliacoes": len(df)} 
    
# endpoint exclusivo p/ mapa 

# --- 8. ENDPOINT DO MAPA (VERSÃO MOCK / TESTE) ---
# Este endpoint devolve dados fixos para o Front-End testar sem precisar da API do Google paga.

# --- ROTAS DE EVENTOS ---

@app.post("/eventos", response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
async def criar_evento(evento_data: EventoCreate, current_user: UsuarioDocument = Depends(get_current_user)):
    novo_evento = EventoDocument(
        nome=evento_data.nome,
        data_inicio=evento_data.data_inicio,
        local=evento_data.local,
        descricao=evento_data.descricao,
        preco=evento_data.preco,
        imagem_url=evento_data.imagem_url
    )
    await novo_evento.insert()
    return novo_evento

@app.get("/eventos", response_model=List[EventoResponse])
async def listar_eventos():
    return await EventoDocument.find_all().to_list()


@app.get("/mapa/pins")
async def get_map_pins(
    tipo: str = "tourist_attraction", 
    radius: int = 5000
):
    """
    Retorna uma lista fixa de pontos turísticos de Caruaru.
    Usado para desenvolvimento e testes do Front-End.
    """
    print("⚠️ TESTE ATIVADO: Enviando dados de teste para o mapa.")
    
    # Lista fixa de lugares reais de Caruaru
    return [
        {
            "titulo": "Alto do Moura",
            "latitude": -8.281927,
            "longitude": -35.992667,
            "place_id": "mock_01",
            "endereco": "Alto do Moura, Caruaru - PE"
        },
        {
            "titulo": "Feira de Caruaru (Parque 18 de Maio)",
            "latitude": -8.283354,
            "longitude": -35.972323,
            "place_id": "mock_02",
            "endereco": "Parque 18 de Maio, Centro"
        },
        {
            "titulo": "Pátio de Eventos Luiz Gonzaga",
            "latitude": -8.285521,
            "longitude": -35.972012,
            "place_id": "mock_03",
            "endereco": "Centro, Caruaru - PE"
        },
        {
            "titulo": "Morro Bom Jesus",
            "latitude": -8.277712,
            "longitude": -35.970145,
            "place_id": "mock_04",
            "endereco": "Divinópolis, Caruaru"
        },
        {
            "titulo": "Caruaru Shopping",
            "latitude": -8.297445,
            "longitude": -35.986878,
            "place_id": "mock_05",
            "endereco": "Av. Adjar da Silva Casé, 800"
        },
        {
            "titulo": "Museu do Barro",
            "latitude": -8.284300,
            "longitude": -35.973100,
            "place_id": "mock_06",
            "endereco": "Praça Cel. José de Vasconcelos, 100"
        }
    ]