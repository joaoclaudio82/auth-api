# 📐 Arquitetura da Auth API — Guia Didático Completo

> Documento técnico e didático que explica **toda** a aplicação nos mínimos detalhes,
> com foco principal na **arquitetura** utilizada.
>
> Stack: **FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Pydantic v2 · JWT (JOSE) · bcrypt/passlib**

---

## 1. O que é este projeto

Uma **API de autenticação de usuários**. Ela faz três coisas essenciais:

1. **Cadastrar** um usuário (`POST /auth/register`).
2. **Logar** e devolver um **token JWT** (`POST /auth/login`).
3. **Identificar** o usuário dono de um token numa **rota protegida** (`GET /users/me`).

Além disso expõe um *healthcheck* (`GET /health`) para saber se o serviço está no ar.

A senha **nunca** é guardada em texto puro: ela é transformada em um **hash bcrypt** antes
de tocar o banco. O acesso às rotas protegidas é feito por **token JWT** assinado.

---

## 2. A grande ideia: Arquitetura em Camadas (Layered Architecture)

O coração do projeto é a **separação de responsabilidades**. Em vez de enfiar tudo dentro
das rotas, cada tipo de trabalho mora em uma camada própria. Isso é conhecido como
**arquitetura em camadas** (ou *N-tier*).

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENTE (Swagger, curl, front-end)            │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ HTTP (JSON / form-urlencoded)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CAMADA 1 — API / ROTAS            app/api/  (auth.py, users.py)        │
│  • Recebe a requisição HTTP                                            │
│  • Valida entrada com schemas Pydantic                                │
│  • Decide o status HTTP (201, 401, 409...)                            │
│  • NÃO contém regra de negócio nem SQL                                │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ chama funções Python puras
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CAMADA 2 — SERVICES               app/services/  (user_service.py)    │
│  • Regra de negócio (ex.: "email é único", "senha bate com o hash?")  │
│  • Orquestra models + segurança                                       │
│  • NÃO conhece HTTP (não levanta HTTPException)                       │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ usa o ORM
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CAMADA 3 — MODELS                 app/models/  (user.py)              │
│  • Mapeia classes Python ⇆ tabelas do banco (SQLAlchemy ORM)          │
│  • Define colunas, tipos, índices e restrições                        │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ SQL via engine
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BANCO DE DADOS — PostgreSQL (rodando em Docker, porta 5433)          │
└──────────────────────────────────────────────────────────────────────┘

   Camadas de apoio (transversais, usadas por todas as outras):
   ┌────────────────────────────────────────────────────────────────┐
   │ app/core/    → config (.env), database (engine/sessão), security│
   │ app/schemas/ → contratos Pydantic de entrada e saída            │
   │ alembic/     → versionamento/migração do banco                  │
   └────────────────────────────────────────────────────────────────┘
```

### Por que separar em camadas?

| Benefício | Como a separação ajuda |
|-----------|------------------------|
| **Manutenção** | Mudou a regra de negócio? Mexe só em `services/`. Mudou a resposta HTTP? Mexe só em `api/`. |
| **Testabilidade** | Dá pra testar `user_service.authenticate()` sem subir o FastAPI inteiro. |
| **Reuso** | A mesma função `create_user()` pode ser chamada por vários endpoints. |
| **Baixo acoplamento** | A camada de serviço não sabe que existe HTTP; o model não sabe que existe Pydantic. |

> 💡 **Regra de ouro do projeto:** a dependência aponta sempre **para baixo**.
> Rota → Serviço → Model → Banco. Nunca o contrário.

---

## 3. Estrutura de pastas (mapa do território)

```text
projeto1/
├── app/
│   ├── main.py               # ① Ponto de entrada: cria o app e registra os routers
│   ├── api/
│   │   ├── auth.py           # ② Rotas /auth/register e /auth/login
│   │   └── users.py          # ③ Rota protegida /users/me + dependência get_current_user
│   ├── core/
│   │   ├── config.py         # ④ Configurações (lidas do .env)
│   │   ├── database.py       # ⑤ Engine, sessão e a dependência get_db
│   │   └── security.py       # ⑥ Hash de senha + criação/decodificação de JWT
│   ├── models/
│   │   └── user.py           # ⑦ Modelo ORM da tabela "users"
│   ├── schemas/
│   │   └── user.py           # ⑧ Schemas Pydantic: UserCreate, UserRead, Token
│   └── services/
│       └── user_service.py   # ⑨ Regra de negócio dos usuários
├── alembic/
│   ├── env.py                # ⑩ Bootstrap das migrations (liga Alembic aos models)
│   └── versions/
│       └── d37ec71b4f0c_create_users_table.py  # ⑪ Migration que cria a tabela users
├── alembic.ini               # Configuração do Alembic
├── requirements.txt          # Dependências do projeto
└── .env                      # Variáveis de ambiente (NÃO versionar segredos reais)
```

---

## 4. Passeio detalhado por cada camada

### ① `app/main.py` — A porta de entrada

```python
from fastapi import FastAPI
from app.api import auth, users

app = FastAPI(title="auth-api-fast", version="1.0.0")

app.include_router(auth.router)   # adiciona /auth/register e /auth/login
app.include_router(users.router)  # adiciona /users/me

@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}
```

**Papel:** é o *composition root* — o lugar onde as peças se juntam. Ele:

- cria a instância `app` do FastAPI (o título e versão aparecem no Swagger);
- **registra os routers** (`include_router`). Cada router já carrega seu próprio prefixo
  (`/auth`, `/users`), então aqui não se repete o caminho;
- define o `/health`, agrupado sob a tag `infra` na documentação.

> 🧩 **Conceito — Router:** o FastAPI permite quebrar as rotas em "mini-aplicações"
> (`APIRouter`). Cada arquivo em `api/` define um router e o `main.py` só os pluga.
> Isso evita um `main.py` gigante e mantém a coesão.

---

### ⑧ `app/schemas/user.py` — Os contratos (Pydantic)

Antes das rotas, é importante entender os **schemas**, porque são eles o "contrato" de
dados que entra e sai da API.

```python
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class UserCreate(BaseModel):                 # ENTRADA do cadastro
    email: EmailStr                          # valida formato de e-mail automaticamente
    password: str = Field(min_length=8, max_length=72,
                          description="Senha entre 8 e 72 caracteres")

class UserRead(BaseModel):                   # SAÍDA segura (nunca expõe a senha!)
    model_config = ConfigDict(from_attributes=True)  # permite ler de objeto ORM
    id: int
    email: EmailStr
    is_active: bool

class Token(BaseModel):                       # SAÍDA do login
    access_token: str
    token_type: str = "bearer"
```

**Três papéis distintos, três schemas:**

| Schema | Direção | Função |
|--------|---------|--------|
| `UserCreate` | Entrada | Valida e-mail + força senha entre 8 e 72 caracteres |
| `UserRead` | Saída | Devolve só `id`, `email`, `is_active` — **omite `hashed_password`** |
| `Token` | Saída | Empacota o JWT no formato `{access_token, token_type}` |

> 🔐 **Detalhe de segurança crucial:** `UserRead` **não tem** o campo `hashed_password`.
> Como a rota declara `response_model=UserRead`, o FastAPI **filtra** a resposta e o hash
> jamais vaza para o cliente — mesmo que o objeto `User` completo seja retornado.

> 🧩 **`from_attributes=True`** (antigo `orm_mode`): autoriza o Pydantic a construir o
> `UserRead` a partir de um objeto SQLAlchemy (lendo `.id`, `.email`...), e não só de um dict.

> 📏 **Por que `max_length=72`?** O algoritmo **bcrypt** trunca silenciosamente senhas
> acima de 72 bytes. Limitar no schema evita comportamento confuso e um erro conhecido
> (relatado na seção de problemas do README).

---

### ⑨ `app/services/user_service.py` — A regra de negócio

Esta é a camada onde mora a "inteligência" da aplicação. Repare que ela usa o **model**
e a **segurança**, mas **não importa nada de HTTP**.

```python
def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),  # ← hash aqui!
    )
    db.add(user)        # coloca na sessão (ainda não gravou)
    db.commit()         # confirma: INSERT INTO users ...
    db.refresh(user)    # recarrega para pegar o id gerado pelo banco
    return user

def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if not user:
        return None                                  # email não existe
    if not verify_password(password, user.hashed_password):
        return None                                  # senha errada
    return user                                      # ok!
```

**Três funções, três responsabilidades:**

- `get_by_email` — consulta simples por e-mail (reutilizada no cadastro e no login).
- `create_user` — encapsula o fluxo `hash → add → commit → refresh`.
- `authenticate` — valida credenciais e devolve `User` ou `None`.

> 🏛️ **Decisão arquitetural importante (documentada no próprio código):**
> o serviço **retorna `None`** em vez de lançar `HTTPException`. Por quê?
> Porque `HTTPException` pertence ao mundo HTTP, que é responsabilidade da **camada de API**.
> O serviço só diz "autenticou" ou "não autenticou" — **quem traduz isso em um 401 é a rota**.
> Isso mantém o serviço independente do protocolo e reutilizável fora da web.

---

### ② `app/api/auth.py` — Rotas de cadastro e login

```python
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if user_service.get_by_email(db, data.email):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    return user_service.create_user(db, data)

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    user = user_service.authenticate(db, email=form.username, password=form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)
```

**O que esta camada faz (e o que NÃO faz):**

- ✅ Recebe e valida o corpo (`UserCreate` para register; `OAuth2PasswordRequestForm` p/ login).
- ✅ Decide os códigos HTTP: `201 Created`, `409 Conflict`, `401 Unauthorized`.
- ✅ Delega a regra para o `user_service`.
- ❌ **Não** faz SQL diretamente. **Não** faz hash. **Não** monta JWT na mão.

> 🧩 **`OAuth2PasswordRequestForm`** é um formulário padrão do OAuth2. Ele espera os campos
> `username` e `password` enviados como **form-urlencoded** (não JSON!). Neste projeto, o
> `username` carrega o **e-mail**. Usar esse formato padrão é o que faz o botão **Authorize**
> do Swagger funcionar de graça.

> 🔁 **Note a injeção de dependência** `db: Session = Depends(get_db)`. Cada requisição
> recebe uma sessão de banco nova e isolada. Falaremos disso em `database.py`.

---

### ③ `app/api/users.py` — A rota protegida e o "guardião"

```python
router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> User:
    email = decode_token(token)                  # JWT → email (ou None se inválido)
    if email is None:
        raise HTTPException(401, "Token inválido ou expirado")
    user = user_service.get_by_email(db, email)
    if user is None:
        raise HTTPException(401, "Usuário não encontrado")
    return user

@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
```

Aqui aparece um dos padrões mais elegantes do FastAPI: **dependência como guardião de rota**.

- `oauth2_scheme` sabe **extrair** o token do header `Authorization: Bearer <token>`.
  Ele **não valida** o JWT — só pega a string.
- `get_current_user` é a dependência que de fato **valida**: decodifica o token, extrai o
  e-mail (`sub`), busca o usuário e devolve o objeto `User`. Se algo falhar, lança `401`.
- `read_me` apenas declara `Depends(get_current_user)`. Se o token for inválido, o FastAPI
  **nem entra** na função — corta com 401 antes. Se for válido, `current_user` já chega pronto.

> 🧩 **Por que isso é poderoso?** Qualquer rota nova que precise de autenticação só precisa
> adicionar `current_user: User = Depends(get_current_user)`. A lógica de validação fica
> num único lugar (DRY).

> 🔎 **`tokenUrl="/auth/login"`** informa ao Swagger onde buscar o token quando você clica
> em **Authorize**. É puramente documental/integração — não muda a lógica de validação.

---

### ④ `app/core/config.py` — Configuração centralizada

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://app:app@localhost:5433/appdb"
    secret_key: str = "troque-em-producao"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    class Config:
        env_file = ".env"

settings = Settings()
```

**Padrão de configuração via objeto único (`settings`).** Vantagens:

- Os valores vêm do arquivo **`.env`** (graças a `pydantic-settings` + `env_file`).
- Há **valores-padrão** embutidos, então o app sobe mesmo sem `.env` em dev.
- O resto do código importa um único `settings` e lê `settings.secret_key`, etc. — sem
  `os.getenv` espalhado pelo projeto.

| Variável | Para que serve |
|----------|----------------|
| `database_url` | String de conexão com o PostgreSQL (driver `psycopg2`, porta `5433`) |
| `secret_key` | Chave secreta que **assina** os JWT (trocar em produção!) |
| `algorithm` | Algoritmo de assinatura do JWT — `HS256` (HMAC + SHA-256) |
| `access_token_expire_minutes` | Validade do token, em minutos (30) |

> ⚠️ **Segurança:** `secret_key` e a senha do banco **não** deveriam ir para o Git em
> produção. O `.env` resolve isso mantendo segredos fora do código-fonte.

---

### ⑤ `app/core/database.py` — Engine, Sessão e `get_db`

```python
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Três conceitos centrais do SQLAlchemy 2.0 vivem aqui:

1. **`engine`** — o "motor" que mantém o *pool* de conexões com o PostgreSQL. É criado
   uma vez, usando a `database_url` do `settings`.
2. **`SessionLocal`** — uma **fábrica de sessões**. Cada chamada `SessionLocal()` abre uma
   nova "conversa" transacional com o banco. (`autocommit=False` → você controla o `commit`.)
3. **`Base`** — a classe-mãe declarativa. **Todo model herda dela**, e é por ela que o
   SQLAlchemy (e o Alembic) descobre quais tabelas existem (`Base.metadata`).

**A joia: `get_db` como dependência.**

```
requisição chega → get_db() abre uma sessão (yield db)
                 → a rota usa essa sessão (faz queries, commit...)
requisição acaba → o finally fecha a sessão (db.close())
```

É um **gerador** (`yield`) usado com `Depends(get_db)`. Garante o ciclo de vida correto:
**uma sessão por requisição**, sempre fechada no fim — mesmo se der erro no meio. Isso evita
vazamento de conexões.

---

### ⑥ `app/core/security.py` — Senhas e Tokens

Esta é a camada de **segurança**, e cuida de duas coisas independentes: **hash de senha**
e **JWT**.

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

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

**Parte A — Hash de senha (bcrypt via passlib):**

- `get_password_hash` transforma `"minhasenha"` em algo como `"$2b$12$abc..."`.
- `verify_password` compara a senha digitada com o hash salvo (sem nunca descriptografar —
  bcrypt é *one-way*).
- bcrypt é **lento de propósito**, o que dificulta ataques de força bruta.

**Parte B — JWT (JSON Web Token):**

- `create_access_token` monta um *payload* com:
  - `sub` (subject) = o e-mail do usuário (quem é o dono do token);
  - `exp` (expiration) = agora + 30 min (calculado em UTC).
  - Depois **assina** com a `secret_key` usando `HS256`.
- `decode_token` faz o caminho inverso: valida assinatura **e** expiração automaticamente.
  Se qualquer coisa falhar (`JWTError`), devolve `None` — e a rota traduz isso em 401.

> 🧩 **Por que JWT?** O token é **autocontido**: o servidor consegue saber quem é o usuário
> e se o token ainda vale **sem consultar o banco para validar o token em si**. Só consulta
> o banco depois, para buscar os dados do usuário. Isso torna a autenticação *stateless*.

---

### ⑦ `app/models/user.py` — O modelo ORM

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
```

Este é o **mapeamento objeto-relacional**: a classe `User` (Python) ⇆ a tabela `users` (SQL).
Usa a sintaxe moderna do SQLAlchemy 2.0 (`Mapped[...]` + `mapped_column`).

| Coluna | Tipo | Restrições | Observação |
|--------|------|-----------|-----------|
| `id` | Integer | PK, indexada | Gerado automaticamente pelo banco |
| `email` | String(255) | único, indexado, NOT NULL | A unicidade impede e-mails duplicados |
| `hashed_password` | String(255) | NOT NULL | Guarda **só o hash**, nunca a senha |
| `is_active` | Boolean | default `True`, NOT NULL | Permite "desativar" usuários no futuro |
| `created_at` | DateTime(tz) | `server_default=now()`, NOT NULL | O **banco** carimba a data de criação |

> 🧩 **`server_default=func.now()`**: a data de criação é definida pelo **PostgreSQL** no
> momento do INSERT, não pelo Python. Mais confiável e consistente entre processos.

> 🧩 **`unique=True` no email**: é a garantia *no nível do banco* de que não há duplicatas.
> A verificação no `register` (que retorna 409) é a primeira linha; o índice único é a rede
> de segurança final.

---

## 5. A camada de Migrations (Alembic)

O banco não é criado "na mão" nem automaticamente pelo app. Ele é versionado com **Alembic**,
o que permite reproduzir exatamente a mesma estrutura em qualquer ambiente.

### ⑩ `alembic/env.py` — A ponte Alembic ↔ aplicação

```python
from app.core.config import settings
from app.core.database import Base
from app.models.user import User          # ← importa o model para registrá-lo na metadata

config.set_main_option("sqlalchemy.url", settings.database_url)  # mesma URL do app
target_metadata = Base.metadata                                  # Alembic "enxerga" os models
```

Dois ajustes tornam o `--autogenerate` possível:

1. **`target_metadata = Base.metadata`** — entrega ao Alembic o catálogo de todas as tabelas
   declaradas via `Base`. Comparando isso com o banco real, ele gera as migrations sozinho.
2. **`config.set_main_option("sqlalchemy.url", settings.database_url)`** — força o Alembic a
   usar **a mesma** `DATABASE_URL` da aplicação (em vez do placeholder do `alembic.ini`).
3. O `import ... User` é necessário para que a classe seja **carregada** e, assim, registrada
   em `Base.metadata`. Sem o import, o Alembic não veria a tabela.

### ⑪ `alembic/versions/d37ec71b4f0c_create_users_table.py` — A migration

```python
def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(...); op.drop_table('users')
```

- **`upgrade()`** — o que fazer para avançar (criar a tabela e os índices).
- **`downgrade()`** — como reverter (derrubar a tabela). Permite voltar atrás com segurança.
- `revision = 'd37ec71b4f0c'` e `down_revision = None` indicam que esta é a **primeira**
  migration da cadeia (não há anterior).

Comandos típicos:

```bash
alembic revision --autogenerate -m "create users table"   # gera a migration
alembic upgrade head                                       # aplica até a última
```

Depois disso o banco tem duas tabelas: **`users`** e **`alembic_version`** (esta última é
controlada pelo Alembic para saber qual migration já foi aplicada).

---

## 6. Fluxos completos (juntando todas as camadas)

### 🟢 Fluxo de cadastro — `POST /auth/register`

```
Cliente envia JSON { email, password }
        │
        ▼
[api/auth.py] register()
  • Pydantic valida UserCreate (email válido? senha 8–72 chars?)
  • pergunta ao serviço: já existe esse email?
        │ get_by_email
        ▼
[services/user_service.py] ── usa ──▶ [models/user.py] ── SQL ──▶ PostgreSQL
        │
        ├─ SE existe → volta para a rota → HTTPException 409 "E-mail já cadastrado"
        │
        └─ SE não existe → create_user()
                 • security.get_password_hash(password)   ← bcrypt
                 • db.add + commit + refresh
                 • devolve objeto User (com id)
        │
        ▼
[api/auth.py] response_model=UserRead filtra a saída
        │
        ▼
Cliente recebe 201 { id, email, is_active }   (sem hashed_password!)
```

### 🔵 Fluxo de login — `POST /auth/login`

```
Cliente envia form-urlencoded { username=email, password }
        │
        ▼
[api/auth.py] login()  (OAuth2PasswordRequestForm)
        │ authenticate(email, password)
        ▼
[services] get_by_email → compara via security.verify_password(senha, hash)
        │
        ├─ inválido → HTTPException 401 "Credenciais inválidas"
        │
        └─ válido → security.create_access_token(subject=email)
                       • payload { sub: email, exp: agora+30min }
                       • assina com secret_key (HS256)
        │
        ▼
Cliente recebe 200 { access_token: "<JWT>", token_type: "bearer" }
```

### 🟣 Fluxo da rota protegida — `GET /users/me`

```
Cliente envia header: Authorization: Bearer <JWT>
        │
        ▼
[api/users.py] oauth2_scheme extrai a string do token
        │
        ▼
get_current_user()
  • security.decode_token(token)  → valida assinatura + expiração → devolve email (sub)
        │
        ├─ token inválido/expirado → 401 "Token inválido ou expirado"
        │
        └─ email ok → get_by_email(email)
                 ├─ usuário não existe → 401 "Usuário não encontrado"
                 └─ existe → devolve User
        │
        ▼
read_me() recebe current_user já pronto
        │
        ▼
Cliente recebe 200 { id, email, is_active }   (UserRead, sem hash)
```

---

## 7. Padrões de projeto presentes (resumo conceitual)

| Padrão / Conceito | Onde aparece | O que entrega |
|-------------------|--------------|---------------|
| **Layered Architecture** | toda a árvore `app/` | Separação clara de responsabilidades |
| **Dependency Injection** | `Depends(get_db)`, `Depends(get_current_user)` | Sessão e usuário injetados automaticamente |
| **Repository/Service Layer** | `services/user_service.py` | Regra de negócio isolada do HTTP e do framework |
| **DTO / Schema** | `schemas/user.py` (Pydantic) | Contratos de entrada/saída e blindagem de dados sensíveis |
| **ORM / Data Mapper** | `models/user.py` (SQLAlchemy) | Classes Python ⇆ tabelas SQL |
| **Settings object** | `core/config.py` (`BaseSettings`) | Configuração centralizada via `.env` |
| **Migration / Versionamento de schema** | `alembic/` | Evolução reproduzível do banco |
| **Stateless Auth (JWT)** | `core/security.py` | Autenticação sem guardar sessão no servidor |
| **Guard Dependency** | `get_current_user` | Proteção reutilizável de rotas |

---

## 8. Stack e dependências (`requirements.txt`)

| Pacote | Papel na arquitetura |
|--------|----------------------|
| `fastapi` | Framework web / camada de API (rotas, validação, OpenAPI/Swagger) |
| `uvicorn[standard]` | Servidor ASGI que executa a aplicação |
| `sqlalchemy` 2.0 | ORM — camada de models e acesso a dados |
| `psycopg2-binary` | Driver de conexão com o PostgreSQL |
| `alembic` | Migrations / versionamento do banco |
| `pydantic` + `pydantic-settings` | Schemas (contratos) e configuração via `.env` |
| `python-jose[cryptography]` | Criação e validação de JWT |
| `passlib[bcrypt]` + `bcrypt` | Hash seguro de senhas |
| `python-multipart` | Necessário para ler formulários (login OAuth2) |
| `pytest`, `httpx` | Ferramentas para testes automatizados (próxima etapa) |

---

## 9. Como rodar (visão rápida)

```bash
# 1) Subir o PostgreSQL em Docker (porta 5433 publicada!)
docker run -d --name pg-auth -p 5433:5432 \
  -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=appdb postgres

# 2) Instalar dependências
pip install -r requirements.txt

# 3) Aplicar as migrations (cria a tabela users)
alembic upgrade head

# 4) Subir a API
uvicorn app.main:app --reload

# 5) Abrir o Swagger
#    http://127.0.0.1:8000/docs
```

> ⚠️ Erros comuns já documentados no README: porta do container não publicada
> (`connection refused on port 5433` → use `-p 5433:5432`), tabela inexistente
> (`relation "users" does not exist` → rode `alembic upgrade head`) e senha do banco
> divergente (`password authentication failed` → confira a `DATABASE_URL`).

---

## 10. Resumo em uma frase

> **Cada arquivo tem um único motivo para mudar.** As rotas (`api/`) só cuidam de HTTP,
> os serviços (`services/`) só cuidam de regra de negócio, os models (`models/`) só
> descrevem o banco, os schemas (`schemas/`) só definem contratos e o `core/` concentra
> infraestrutura (config, conexão, segurança). É essa disciplina de **separação de
> responsabilidades** que torna a Auth API limpa, testável e pronta para crescer.
```
