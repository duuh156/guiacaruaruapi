
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from pydantic import Field
from typing import Optional
import os

# --- SEU LINK DO MONGODB ATLAS AQUI ---
# Substitua pela sua string de conexão REAL
MONGO_URL = os.getenv("MONGO_DB_URL")

# Modelo de Evento (para garantir que não depende de outros arquivos)
class EventoDocument(Document):
    nome: str
    data_inicio: str
    local: str
    descricao: str
    preco: float
    imagem_url: Optional[str] = None
    
    class Settings:
        name = "eventos"

async def popular_banco():
    print(f"🔄 Tentando conectar em: {MONGO_URL[:20]}...") # Mostra o começo do link para conferir

    try:
        # Cria o cliente usando EXPLICITAMENTE a variável MONGO_URL
        client = AsyncIOMotorClient(MONGO_URL)
        
        # Pega o banco de dados 'guia_caruaru_db'
        db = client.get_database("guia_caruaru_db")
        
        # Inicializa o Beanie
        await init_beanie(database=db, document_models=[EventoDocument])
        print("✅ Conexão bem sucedida!")

        print("🚀 Criando eventos...")
        eventos = [
            {
                "nome": "Vidinha de Balada - Henrique e Juliano",
                "data_inicio": "12/12/2025 20:00",
                "local": "Estacionamento do Polo Caruaru",
                "descricao": "O show mais esperado do ano! Henrique e Juliano, Nattan e convidados.",
                "preco": 120.00,
                "imagem_url": "https://agendadeshows.com.br/wp-content/uploads/2024/10/henrique-e-juliano-agenda.jpg"
            },
            {
                "nome": "Bregou Festival Caruaru",
                "data_inicio": "06/12/2025 21:00",
                "local": "Arena Caruaru",
                "descricao": "O maior festival de Brega do agreste pernambucano.",
                "preco": 70.00,
                "imagem_url": "https://ingressosprime.com/images/events/bregou-festival-caruaru.jpg"
            },
            {
                "nome": "Natal Luz Caruaru",
                "data_inicio": "24/12/2025 19:00",
                "local": "Centro da Cidade",
                "descricao": "Decoração especial e apresentações culturais gratuitas.",
                "preco": 0.00,
                "imagem_url": "https://conheca.caruaru.pe.gov.br/wp-content/uploads/2022/12/seresta.jpg"
            }
        ]

        for evento in eventos:
            novo = EventoDocument(**evento)
            await novo.insert()
            print(f"  -> Criado: {evento['nome']}")

        print("🎉 Sucesso! Eventos criados na nuvem.")

    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")

if __name__ == "__main__":
    asyncio.run(popular_banco())