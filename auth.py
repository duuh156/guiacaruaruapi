from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends,HTTPException, status
from models import UsuarioDocument
from typing import Optional
import os 
from dotenv import load_dotenv


load_dotenv()

#  CONIGURAÇÃO DE SEGURANÇA

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES",60))

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth2_schemas = OAuth2PasswordBearer(tokenUrl="login")

# FUNÇÃO LOGICA DE SEGURANÇA 

def hash_password(password: str) -> str:
   """criptografia a senha (Segurança).""" 
   return pwd_context.hash(password)

def verify_password(plain_password: str,hashed_password: str) -> bool:
    """Compara a senha (logica de programação)."""
    return pwd_context.verify(plain_password,hashed_password)

def create_access_token(data: dict,expires_delta: Optional[timedelta] = None):
    """Cria o JWT (Segurança)."""
    to_encode = data.copy()

    if  expires_delta:
        expire = datetime.utcnow() + expires_delta

    else:
        expire = datetime.utcnow() + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire,"iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

# FUNÇÃO DEPENDETE 
async def get_current_user(token: str = Depends(oauth2_schemas)) -> "UsuarioDocument":
    """verifica o token e retorna o usuario logado"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Autenticate": "Bearer"}
    )

    try:
        # DECODIFICA E VERIFICA A ASSINATURA TOKEN 
        payload = jwt.decode(token,SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")

        if user_email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    #BUSCA O USUARIO NO BANCO DE DADOS 
    user = await UsuarioDocument.find_one({"email":user_email})

    if user is None:
        raise credentials_exception

    return user
