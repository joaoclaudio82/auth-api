import os

#create_engine do SQLAlchemy. Ele é usado para criar uma conexão 
# com o banco de dados usando a URL fornecida.
from sqlalchemy import create_engine 

#Importa as classes e funções necessárias do SQLAlchemy para 
# definir modelos de banco de dados e criar sessões de banco de dados.
from sqlalchemy.orm import DeclarativeBase, declarative_base, sessionmaker 
from app.core.config import settings

#Importa o objeto settings do módulo app.core.config. Ele contém as configurações do projeto, como a URL do banco de dados, chaves de API, etc.
engine = create_engine(settings.database_url)

#Cria um objeto engine usando a URL do banco de dados definida em settings.database_url. 
# Este objeto é usado para se conectar ao banco de dados.
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

#Cria uma classe base para os modelos de banco de dados usando declarative_base. 
# Esta classe é usada como base para todas as classes de modelo que definimos posteriormente.
class Base(DeclarativeBase):
    pass #A classe Base é uma classe vazia que herda de DeclarativeBase. Ela serve como base para os 
        #modelos de banco de dados, permitindo que eles sejam definidos como classes Python normais.

def get_db():
    """Dependência do FastAPI:abre sessão por requisição e fecha no fim."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()