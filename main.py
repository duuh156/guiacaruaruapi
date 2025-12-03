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
        email=user.email, nome=user.nome, senha_hash=hashed_password)
    await new_user.insert()
    return new_user

# main.py - Substitua a função login por esta:

@app.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"👀 DEBUG: Tentando logar com o email: {form_data.username}")
    
    # 1. Busca o usuário
    user = await UsuarioDocument.find_one(UsuarioDocument.email == form_data.username)
    
    if not user:
        print("❌ DEBUG: Usuário NÃO encontrado no banco de dados.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Usuário achado. Vamos ver o que tem na senha_hash
    print(f"✅ DEBUG: Usuário encontrado: {user.nome}")
    print(f"🔑 DEBUG: Hash salvo no banco: {user.senha_hash}")
    print(f"⌨️ DEBUG: Senha digitada: {form_data.password}")
    
    # 3. Verifica a senha
    senha_valida = verify_password(form_data.password, user.senha_hash)
    print(f"🤔 DEBUG: A senha confere? {senha_valida}")

    if not senha_valida:
        print("❌ DEBUG: Senha INVÁLIDA (O hash não bateu).")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. TENTATIVA DE CRIAR TOKEN (COM DEBUG DE ERRO)
    print("🚀 DEBUG: Senha correta! Tentando criar o token...")
    
    try:
        access_token_expires = timedelta(minutes=float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)))
        
        # Vamos imprimir as variáveis para garantir que elas existem
        print(f"🔑 DEBUG: Usando Secret Key: {os.getenv('SECRET_KEY')}")
        print(f"🧮 DEBUG: Usando Algoritmo: {os.getenv('ALGORITHM', 'HS256')}")

        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        print(f"🎫 DEBUG: Token criado com sucesso: {access_token[:10]}...") # Mostra só o começo
        
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print(f"💥 ERRO FATAL AO CRIAR TOKEN: {e}") # <--- AQUI VAI APARECER O MOTIVO
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao gerar token: {str(e)}"
        )
        
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


# --- 8. ENDPOINT DO MAPA E FOTO
@app.get("/mapa/pins")
async def get_map_pins(
    tipo: str = "tourist_attraction", 
    radius: int = 5000
):
    """
    Retorna locais com NOME, COORDENADAS e FOTO (URL).
    """
    try:
        results = gmaps.places_nearby(
            location=CARUARU_LOCATION,
            radius=radius,
            language='pt-BR',
            type=tipo
        )
        
        pins = []
        for lugar in results.get('results', []):
            geo = lugar.get('geometry', {}).get('location', {})
            
            # --- NOVA LÓGICA PARA PEGAR A FOTO ---
            foto_url = None
            photos = lugar.get('photos', [])
            if photos:
                # Pega o código da primeira foto
                ref = photos[0].get('photo_reference')
                # Monta o link completo usando sua chave
                foto_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={GOOGLE_MAPS_API_KEY}"

            pins.append({
                "titulo": lugar.get('name'),
                "latitude": geo.get('lat'),
                "longitude": geo.get('lng'),
                "place_id": lugar.get('place_id'),
                "endereco": lugar.get('vicinity'),
                "imagem": foto_url # <--- O Front-End vai usar este link aqui!
            })
            
        return pins

    except Exception as e:
        print(f"Erro ao buscar no Google: {e}")
        raise HTTPException(status_code=503, detail="Erro ao buscar dados do Google Maps.")