# Componente `tests/` — Testes automatizados (Pytest)

> Pasta: [`tests/`](../../tests/) · configuração: [`pytest.ini`](../../pytest.ini)
> Arquivos: `conftest.py`, `test_auth.py`

A pasta `tests/` contém os **testes automatizados** da API, escritos com **pytest**. Eles verificam, sem intervenção manual, se o cadastro, o login e a rota protegida funcionam — inclusive os cenários de erro.

> 🧩 **Ideia central:** os testes **não** usam o PostgreSQL real. Eles sobem um **SQLite em memória**, isolado e descartável, para que cada execução seja rápida, repetível e não suje o banco de verdade.

---

## `pytest.ini` — Configuração

```ini
[pytest]
pythonpath = .          # permite "import app" a partir da raiz do projeto
testpaths = tests       # o pytest procura testes só na pasta tests/
```

- `pythonpath = .` adiciona a raiz do projeto ao `sys.path`, então `from app.main import app` funciona nos testes.
- `testpaths = tests` diz ao pytest onde procurar os arquivos de teste.

---

## `conftest.py` — O ambiente de teste

Este arquivo é especial: o pytest o carrega **automaticamente** e disponibiliza suas *fixtures* para todos os testes. Ele faz três coisas:

### 1. Define variáveis de ambiente ANTES de importar o app

```python
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-more-than-32-characters")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
```

> ⚠️ **Por que isso vem antes dos imports?** Lembre-se de que `config.py` exige `DATABASE_URL` e `SECRET_KEY` (não têm default). Como o `settings = Settings()` roda no momento do import, essas variáveis precisam **já existir** antes de `from app.main import app`. Por isso elas são definidas no topo do arquivo.

### 2. Cria um banco SQLite em memória

```python
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

- `"sqlite://"` → banco **em memória** (some quando o processo acaba).
- `StaticPool` + `check_same_thread=False` → garante que **a mesma conexão** seja reutilizada em todo o teste. Sem isso, cada conexão veria um banco em memória diferente (vazio).

### 3. A fixture `client` — substitui o banco real pelo de teste

```python
@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)        # cria as tabelas no SQLite

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db   # troca a dependência!

    yield TestClient(app)                        # entrega o cliente aos testes

    Base.metadata.drop_all(bind=engine)          # limpa as tabelas
    app.dependency_overrides.clear()             # restaura a dependência original
```

O segredo está no **`app.dependency_overrides[get_db] = override_get_db`**: ele diz ao FastAPI "sempre que alguém pedir `get_db`, use esta versão de teste em vez da real". É exatamente por `get_db` ser uma **dependência injetável** ([core.md](core.md)) que conseguimos trocar o banco sem alterar uma linha do código de produção.

O fluxo de cada teste:
```
cria tabelas → entrega o TestClient → roda o teste → apaga tabelas → limpa overrides
```
Assim, **cada teste começa com um banco limpo**.

---

## `test_auth.py` — Os casos de teste

Cada função `test_*` recebe a fixture `client` como argumento e testa um cenário:

| Teste | O que valida | Espera |
|-------|--------------|--------|
| `test_register` | Cadastro com sucesso; resposta **não** traz `hashed_password` | `201` |
| `test_register_email_duplicado` | Cadastrar o mesmo e-mail duas vezes | `409` + mensagem |
| `test_login_e_users_me` | Fluxo completo: registra → loga → acessa `/users/me` com o token | `200` |
| `test_users_me_sem_token` | Acessar rota protegida **sem** token | `401` |

Exemplo (o teste do fluxo completo):

```python
def test_login_e_users_me(client):
    payload = {"email": "joao@teste.com", "password": "senha123456"}
    client.post("/auth/register", json=payload)

    login = client.post("/auth/login",
        data={"username": "joao@teste.com", "password": "senha123456"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "joao@teste.com"
```

> 🔎 Note que o register manda **JSON** (`json=...`) e o login manda **form-urlencoded** (`data=...`) — exatamente como as rotas esperam (veja [api.md](api.md)).

---

## Como rodar os testes

```bash
pytest                 # roda todos os testes
pytest -v              # modo verboso (mostra cada teste)
pytest tests/test_auth.py::test_register   # roda um teste específico
```

Não é preciso ter o PostgreSQL nem o Docker rodando — os testes usam o SQLite em memória.

🔗 Veja também: [core.md](core.md) (a dependência `get_db` que é substituída), [api.md](api.md) (as rotas testadas).
