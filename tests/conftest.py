#aqui definimos a configuração para os testes usando pytest. 
# Criamos um banco de dados SQLite em memória para isolar os testes do banco de dados real.
# A fixture client é responsável por configurar o ambiente de teste, incluindo a criação das tabelas e a substituição da dependência get_db 
# para usar o banco de dados de teste. Após os testes, as tabelas são removidas e as dependências são limpas para garantir que cada teste seja executado em um ambiente limpo.
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-more-than-32-characters")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# aqui criamos um banco de dados SQLite em memória para os testes, usando StaticPool para garantir que a mesma conexão seja usada em todos os testes.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
#aqui criamos uma sessão de banco de dados para os testes, usando sessionmaker para configurar a sessão com as opções apropriadas para o SQLite em memória.
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

#aqui definimos uma fixture do pytest chamada client, que é responsável por configurar o ambiente de teste para os testes de integração.
@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
#aqui definimos uma função override_get_db que substitui a dependência get_db para usar o banco de dados de teste.
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db #aqui usamos yield para criar um gerador que fornece a sessão de banco de dados para os testes. O bloco try-finally garante que a sessão seja fechada corretamente após o teste, mesmo que ocorra uma exceção durante o teste.
        finally:
            db.close()
    #aqui substituímos a dependência get_db no aplicativo FastAPI para usar a função override_get_db, garantindo que os testes usem o banco de dados de teste em vez do banco de dados real.
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)#aqui criamos um cliente de teste usando TestClient do FastAPI, que permite enviar requisições HTTP para o aplicativo durante os testes. 
    #O yield retorna o cliente para os testes, e após os testes, as tabelas do banco de dados são removidas e as dependências são limpas para garantir que cada teste seja executado em um ambiente limpo.

    Base.metadata.drop_all(bind=engine) #aqui removemos as tabelas do banco de dados de teste após os testes, garantindo que cada teste seja executado em um ambiente limpo.
    app.dependency_overrides.clear() #aqui limpamos as dependências substituídas após os testes, garantindo que as dependências originais sejam restauradas para outros testes ou para a execução normal do aplicativo.