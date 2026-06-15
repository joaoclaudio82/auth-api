#aqui definimos a configuração para os testes usando pytest.
# Criamos um banco de dados SQLite em memória para isolar os testes do banco de dados real.
# A fixture client configura o ambiente de teste (criação das tabelas e substituição de get_db).
# A fixture db_session expõe a MESMA sessão usada pela API, permitindo que o teste inspecione/altere
# dados diretamente no banco (ex.: desativar um usuário). Após cada teste, as tabelas são removidas
# e as dependências limpas, garantindo um ambiente isolado.
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


@pytest.fixture()
def db_session():
    """Sessão de banco de teste (SQLite em memória).

    Cria as tabelas antes do teste e as derruba depois, garantindo isolamento.
    Esta MESMA sessão é reutilizada pela fixture client (via override de get_db),
    então alterações feitas aqui são enxergadas pelos endpoints durante o teste.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """TestClient do FastAPI que usa a mesma sessão da fixture db_session.

    Substitui a dependência get_db para que os endpoints usem o banco de teste
    em vez do banco real, sem alterar uma linha do código de produção.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            # o fechamento/limpeza fica a cargo da fixture db_session
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()  # restaura a dependência original após o teste
