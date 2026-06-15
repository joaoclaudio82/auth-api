# Componente `core/` — Infraestrutura base

> Pasta: [`app/core/`](../../app/core/)
> Arquivos: `config.py`, `database.py`, `security.py`

O `core/` é a camada **transversal** (de apoio): não tem regra de negócio nem rotas, mas é usada por **todas** as outras camadas. Aqui ficam três responsabilidades de infraestrutura: **configuração**, **conexão com o banco** e **segurança**.

---

## `config.py` — Configuração centralizada

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

**O que faz:** define um objeto único `settings` que carrega as configurações do arquivo `.env`.

| Variável | Para que serve | Tem default? |
|----------|----------------|--------------|
| `database_url` | String de conexão com o PostgreSQL | ❌ **Obrigatória** |
| `secret_key` | Chave que **assina** os tokens JWT | ❌ **Obrigatória** |
| `algorithm` | Algoritmo de assinatura do JWT | ✅ `HS256` |
| `access_token_expire_minutes` | Validade do token em minutos | ✅ `30` |

> ⚠️ **Atenção:** `database_url` e `secret_key` **não têm valor-padrão**. Se elas não estiverem no `.env` (ou nas variáveis de ambiente), a aplicação **nem sobe** — o Pydantic lança um erro de validação na hora do `Settings()`. Isso é proposital: força que esses valores sejam sempre definidos explicitamente.

**Por que esse padrão é bom?**
- Os segredos ficam **fora do código** (no `.env`, que não vai para o Git).
- O resto do projeto importa um único `settings` e lê `settings.secret_key`, em vez de `os.getenv(...)` espalhado.
- A validação de tipos é automática (ex.: `access_token_expire_minutes` sempre vira `int`).

---

## `database.py` — Engine, Sessão e `get_db`

```python
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """Dependência do FastAPI: abre sessão por requisição e fecha no fim."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Três peças centrais do SQLAlchemy 2.0 vivem aqui:

1. **`engine`** — o "motor" que mantém o *pool* de conexões com o PostgreSQL. Criado uma única vez, a partir da `database_url`.
2. **`SessionLocal`** — uma **fábrica de sessões**. Cada `SessionLocal()` abre uma nova "conversa" transacional com o banco. Como `autocommit=False`, **você** controla quando dar `commit`.
3. **`Base`** — a classe-mãe de todos os models. É por ela (`Base.metadata`) que o SQLAlchemy e o Alembic descobrem quais tabelas existem.

### A joia: `get_db` como dependência

`get_db` é um **gerador** (usa `yield`) consumido via `Depends(get_db)` nas rotas. Ele garante o ciclo de vida correto da sessão:

```
requisição chega  → get_db() abre a sessão (yield db)
a rota usa db     → faz queries, commit...
requisição acaba  → o finally fecha (db.close())  ← mesmo se der erro no meio
```

Resultado: **uma sessão por requisição**, sempre fechada no fim. Isso evita vazamento de conexões.

> 💡 Nos testes, essa dependência é **substituída** por uma versão que aponta para um SQLite em memória (veja [tests.md](tests.md)). É justamente por `get_db` ser injetável que isso funciona sem alterar o código de produção.

---

## `security.py` — Senhas e Tokens

Cuida de **duas coisas independentes**: hash de senha e JWT.

### Parte A — Hash de senha (bcrypt via passlib)

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

- `get_password_hash` transforma `"minhasenha"` em algo como `"$2b$12$abc..."`.
- `verify_password` compara a senha digitada com o hash salvo — **sem nunca descriptografar** (bcrypt é *one-way*).
- bcrypt é **lento de propósito**: isso dificulta ataques de força bruta.

### Parte B — JWT (JSON Web Token)

```python
def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key,
                             algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None
```

- `create_access_token` monta um *payload* com `sub` (o e-mail do dono) e `exp` (expiração = agora + 30 min, em UTC) e **assina** com a `secret_key` usando `HS256`.
- `decode_token` faz o inverso: valida assinatura **e** expiração automaticamente. Se algo falhar (`JWTError`), devolve `None` — e a camada de rota traduz isso em `401`.

> 🧩 **Por que JWT?** O token é **autocontido**: o servidor sabe quem é o usuário e se o token ainda vale **sem precisar consultar o banco para validar o token**. Isso torna a autenticação *stateless*.

---

## Resumo

| Arquivo | Entrega | Quem usa |
|---------|---------|----------|
| `config.py` | Objeto `settings` lido do `.env` | Todo o projeto |
| `database.py` | `engine`, `SessionLocal`, `Base`, `get_db` | rotas, models, alembic, testes |
| `security.py` | hash de senha + JWT | `services/` e `api/` |

🔗 Veja também: [models.md](models.md) (usa `Base`), [services.md](services.md) (usa `security`), [api.md](api.md) (usa `get_db`).
