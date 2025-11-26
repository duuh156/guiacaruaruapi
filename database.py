from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorClient 
from beanie import init_beanie
load_dotenv()

async def init_db():
    # importação local
    from models import UsuarioDocument, FavoritoDocument, AvaliacaoDocument

    MONGO_DB_URL = os.getenv("MONGO_DB_URL")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "guia_caruaru_db")
# 1 criando cliente 

    client = AsyncIOMotorClient(MONGO_DB_URL)

# 2 inicializa o beanie

    await init_beanie(
        database=client[MONGO_DB_NAME],
            document_models=[UsuarioDocument, FavoritoDocument, AvaliacaoDocument]
)
    print(f"Conexão com MongoDB '{MONGO_DB_NAME}' estabelecida.")
