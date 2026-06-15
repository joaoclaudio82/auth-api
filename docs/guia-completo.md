# Auth API — Documentação Completa do Projeto

> API de autenticação de usuários com **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**, **Pydantic v2**, **JWT** e **bcrypt**.
>
> Este documento consolida visão geral, arquitetura, componentes, testes, Docker, CI e instruções de execução.
>
> Entrada rápida: [README.md](../README.md) · Índice: [docs/README.md](README.md)

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Stack tecnológica](#2-stack-tecnológica)
3. [Arquitetura em camadas](#3-arquitetura-em-camadas)
4. [Estrutura de pastas](#4-estrutura-de-pastas)
5. [Endpoints da API](#5-endpoints-da-api)
6. [Componentes em detalhe](#6-componentes-em-detalhe)
7. [Fluxos completos](#7-fluxos-completos)
8. [Migrations (Alembic)](#8-migrations-alembic)
9. [Testes automatizados](#9-testes-automatizados)
10. [Docker e empacotamento](#10-docker-e-empacotamento)
11. [CI/CD](#11-cicd)
12. [Padrões de projeto](#12-padrões-de-projeto)
13. [Problemas comuns](#13-problemas-comuns)
14. [Como rodar o projeto](#14-como-rodar-o-projeto)

---

## 1. Visão geral

Este projeto é uma **API de autenticação de usuários**. Em poucas palavras, ela faz três coisas essenciais:

1. **Cadastrar** um usuário — `POST /auth/register`
2. **Logar** e devolver um **token JWT** — `POST /auth/login`
3. **Identificar** o dono de um token numa **rota protegida** — `GET /users/me`

Além disso, expõe um *healthcheck* (`GET /health`) para verificar se o serviço está no ar.

### Garantias de segurança

- A senha **nunca** é guardada em texto puro — vira um **hash bcrypt** antes de tocar o banco.
- O acesso às rotas protegidas é feito por **token JWT assinado**, com validade (expiração).
- O schema de saída `UserRead` **omite** o campo `hashed_password`, impedindo vazamento do hash nas respostas.

### O que foi implementado

| Funcionalidade | Descrição |
|----------------|-----------|
| Cadastro | Valida e-mail e senha, verifica duplicata, persiste com hash |
| Login | Autentica credenciais e retorna JWT |
| Rota protegida | Valida token, identifica usuário e retorna dados seguros |
| Migrations | Tabela `users` criada via Alembic (versionada) |
| Testes | Suíte pytest com cenários de sucesso e erro |
| Docker | `Dockerfile` + `docker-compose.yml` para subir API + banco |
| CI | GitHub Actions roda `pytest` em push e pull request |

---

## 2. Stack tecnológica

| Pacote | Papel |
|--------|-------|
| `fastapi` | Framework web — rotas, validação, OpenAPI/Swagger |
| `uvicorn[standard]` | Servidor ASGI |
| `sqlalchemy` 2.0 | ORM — models e acesso a dados |
| `psycopg2-binary` | Driver PostgreSQL |
| `alembic` | Migrations / versionamento do banco |
| `pydantic` + `pydantic-settings` | Schemas e configuração via `.env` |
| `python-jose[cryptography]` | Criação e validação de JWT |
| `passlib[bcrypt]` + `bcrypt` | Hash seguro de senhas |
| `python-multipart` | Leitura de formulários (login OAuth2) |
| `email-validator` | Validação de e-mail nos schemas |
| `pytest` + `httpx` | Testes automatizados |

---

## 3. Arquitetura em camadas

O coração do projeto é a **separação de responsabilidades**. Cada tipo de trabalho mora em uma camada própria (*layered architecture*).

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CLIENTE (Swagger, curl, front-end)                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTP (JSON / form-urlencoded)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CAMADA 1 — API / ROTAS            app/api/  (auth.py, users.py)     │
│  • Recebe a requisição HTTP                                          │
│  • Valida entrada com schemas Pydantic                               │
│  • Decide o status HTTP (201, 401, 409...)                           │
│  • NÃO contém regra de negócio nem SQL                               │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ chama funções Python puras
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CAMADA 2 — SERVICES               app/services/  (user_service.py)  │
│  • Regra de negócio ("email é único?", "senha bate com o hash?")     │
│  • Orquestra models + segurança                                      │
│  • NÃO conhece HTTP (não levanta HTTPException)                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ usa o ORM
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CAMADA 3 — MODELS                 app/models/  (user.py)           │
│  • Mapeia classes Python ⇆ tabelas do banco (SQLAlchemy ORM)         │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ SQL via engine
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BANCO DE DADOS — PostgreSQL (Docker, porta 5434 no host)            │
└──────────────────────────────────────────────────────────────────────┘

   Camadas de apoio (transversais):
   ┌────────────────────────────────────────────────────────────────┐
   │ app/core/    → config (.env), database (engine/sessão), security│
   │ app/schemas/ → contratos Pydantic de entrada e saída            │
   │ alembic/     → versionamento/migração do banco                  │
   │ tests/       → testes automatizados                             │
   └────────────────────────────────────────────────────────────────┘
```

### Regra de ouro

A dependência aponta sempre **para baixo**: Rota → Serviço → Model → Banco. Nunca o contrário.

| Benefício | Como a separação ajuda |
|-----------|------------------------|
| **Manutenção** | Mudou regra de negócio? Mexe só em `services/`. Mudou resposta HTTP? Mexe só em `api/`. |
| **Testabilidade** | Dá pra testar `user_service.authenticate()` sem subir o FastAPI inteiro. |
| **Reuso** | A mesma função `create_user()` serve a vários endpoints. |
| **Baixo acoplamento** | O serviço não sabe que existe HTTP; o model não sabe que existe Pydantic. |

> **Cada arquivo tem um único motivo para mudar.** As rotas só cuidam de HTTP, os serviços só de regra de negócio, os models só descrevem o banco, os schemas só definem contratos, e o `core/` concentra a infraestrutura.

---

## 4. Estrutura de pastas

```text
auth-api/
├── app/
│   ├── main.py               # Ponto de entrada: cria o app e registra os routers
│   ├── api/
│   │   ├── auth.py           # Rotas /auth/register e /auth/login
│   │   └── users.py          # Rota protegida /users/me + get_current_user
│   ├── core/
│   │   ├── config.py         # Configurações (lidas do .env)
│   │   ├── database.py       # Engine, sessão e dependência get_db
│   │   └── security.py       # Hash de senha + criação/decodificação de JWT
│   ├── models/
│   │   └── user.py           # Modelo ORM da tabela "users"
│   ├── schemas/
│   │   └── user.py           # Schemas Pydantic: UserCreate, UserRead, Token
│   └── services/
│       └── user_service.py   # Regra de negócio dos usuários
├── alembic/
│   ├── env.py                # Bootstrap das migrations
│   └── versions/
│       └── d37ec71b4f0c_create_users_table.py
├── tests/
│   ├── conftest.py           # Fixtures: banco SQLite em memória + TestClient
│   └── test_auth.py          # Testes de cadastro, login e rota protegida
├── docs/                     # Documentação modular do projeto
├── .github/workflows/ci.yml  # Pipeline de CI
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── .env                      # Variáveis de ambiente (não versionar)
```

---

## 5. Endpoints da API

| Método | Caminho | Entrada | Saída | Códigos |
|--------|---------|---------|-------|---------|
| `GET` | `/health` | — | `{"status":"ok"}` | `200` |
| `POST` | `/auth/register` | `UserCreate` (JSON) | `UserRead` | `201`, `409`, `422` |
| `POST` | `/auth/login` | form `username` + `password` | `Token` | `200`, `401` |
| `GET` | `/users/me` | header `Bearer <token>` | `UserRead` | `200`, `401`, `403` |

### Exemplos de resposta

**Cadastro (`201 Created`):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true
}
```

**Login (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Usuário autenticado (`200 OK`):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true
}
```

---

## 6. Componentes em detalhe

### 6.1 `app/main.py` — Ponto de entrada

- Cria a instância `FastAPI(title="auth-api-fast", version="1.0.0")`.
- Registra os routers de `auth` e `users`.
- Expõe `GET /health` (tag `infra` no Swagger).

### 6.2 `app/schemas/user.py` — Contratos Pydantic

| Schema | Direção | Função |
|--------|---------|--------|
| `UserCreate` | Entrada | Valida e-mail + senha entre 8 e 72 caracteres |
| `UserRead` | Saída | Devolve `id`, `email`, `is_active` — **omite `hashed_password`** |
| `Token` | Saída | Empacota JWT como `{access_token, token_type}` |

Detalhes importantes:
- `EmailStr` valida formato de e-mail (422 se inválido).
- `max_length=72` evita truncamento silencioso do bcrypt.
- `from_attributes=True` permite construir `UserRead` a partir de objetos ORM.

### 6.3 `app/models/user.py` — Modelo ORM

Tabela `users`:

| Coluna | Tipo | Restrições | Observação |
|--------|------|-----------|-----------|
| `id` | Integer | PK, indexada | Gerado automaticamente |
| `email` | String(255) | único, indexado, NOT NULL | Impede e-mails duplicados |
| `hashed_password` | String(255) | NOT NULL | Guarda **só o hash** |
| `is_active` | Boolean | default `True`, NOT NULL | Permite desativar usuários |
| `created_at` | DateTime(tz) | `server_default=now()`, NOT NULL | Carimbo do PostgreSQL |

### 6.4 `app/services/user_service.py` — Regra de negócio

| Função | Entrada | Saída | Responsabilidade |
|--------|---------|-------|------------------|
| `get_by_email` | `db`, `email` | `User \| None` | Consulta por e-mail |
| `create_user` | `db`, `UserCreate` | `User` | Hash → add → commit → refresh |
| `authenticate` | `db`, `email`, `password` | `User \| None` | Valida credenciais |

Decisão arquitetural: o serviço **retorna `None`** (ou `ValueError` em corrida de duplicata) em vez de lançar `HTTPException`. Quem traduz em status HTTP é a camada `api/`.

### 6.5 `app/api/auth.py` — Cadastro e login

- `POST /auth/register`: verifica duplicata → `409`; cria usuário → `201`.
- `POST /auth/login`: usa `OAuth2PasswordRequestForm` (form-urlencoded, não JSON). O campo `username` carrega o **e-mail**. Retorna JWT ou `401`.

### 6.6 `app/api/users.py` — Rota protegida

- `oauth2_scheme` extrai o token do header `Authorization: Bearer <token>`.
- `get_current_user` decodifica JWT, busca usuário, verifica `is_active`.
- `GET /users/me` usa `Depends(get_current_user)` — padrão reutilizável para futuras rotas protegidas.

Códigos de erro:
- `401` — token inválido/expirado ou usuário não encontrado.
- `403` — usuário inativo.

### 6.7 `app/core/config.py` — Configuração

Variáveis lidas do `.env`:

| Variável | Função | Obrigatória? |
|----------|--------|--------------|
| `DATABASE_URL` | Conexão com PostgreSQL | Sim |
| `SECRET_KEY` | Assina os tokens JWT | Sim |
| `ALGORITHM` | Algoritmo de assinatura | Não (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token | Não (default: `30`) |

Se `DATABASE_URL` ou `SECRET_KEY` faltarem, a aplicação **não inicia**.

### 6.8 `app/core/database.py` — Banco de dados

- `engine` — pool de conexões com PostgreSQL.
- `SessionLocal` — fábrica de sessões (`autocommit=False`).
- `Base` — classe-mãe dos models (`Base.metadata` para Alembic).
- `get_db()` — dependência FastAPI: **uma sessão por requisição**, sempre fechada no `finally`.

### 6.9 `app/core/security.py` — Segurança

**Hash de senha (bcrypt):**
- `get_password_hash()` — transforma senha em hash one-way.
- `verify_password()` — compara senha digitada com hash salvo.

**JWT:**
- `create_access_token(subject)` — payload `{sub: email, exp: agora+30min}`, assinado com `HS256`.
- `decode_token(token)` — valida assinatura e expiração; retorna e-mail ou `None`.

---

## 7. Fluxos completos

### Cadastro — `POST /auth/register`

```
Cliente envia JSON { email, password }
 → [api/auth] valida UserCreate
 → get_by_email: email já existe?
   → sim  → 409 "E-mail já cadastrado"
   → não  → create_user: hash bcrypt, INSERT, refresh
 → response_model=UserRead filtra a saída
 → Cliente recebe 201 { id, email, is_active }
```

### Login — `POST /auth/login`

```
Cliente envia form { username=email, password }
 → [api/auth] OAuth2PasswordRequestForm
 → authenticate: busca por email, verify_password
   → inválido → 401 "Credenciais inválidas"
   → válido   → create_access_token(email)
 → Cliente recebe 200 { access_token, token_type: "bearer" }
```

### Rota protegida — `GET /users/me`

```
Cliente envia Authorization: Bearer <JWT>
 → oauth2_scheme extrai o token
 → get_current_user:
   → decode_token → email (ou None)
   → get_by_email → User (ou None)
   → verifica is_active
 → falha → 401 ou 403
 → ok    → 200 { id, email, is_active }
```

---

## 8. Migrations (Alembic)

O banco é versionado com **Alembic** — não criado manualmente.

### `alembic/env.py`

- Usa a mesma `DATABASE_URL` da aplicação.
- `target_metadata = Base.metadata` — Alembic enxerga os models.
- Importa `User` para registrá-lo na metadata.

### Migration `d37ec71b4f0c_create_users_table`

- `upgrade()` — cria tabela `users` + índices.
- `downgrade()` — remove tabela e índices.
- Primeira migration da cadeia (`down_revision = None`).

### Comandos

```bash
alembic revision --autogenerate -m "descrição da mudança"
alembic upgrade head
alembic downgrade -1
alembic current
```

Após `upgrade head`, o banco terá `users` e `alembic_version`.

---

## 9. Testes automatizados

### Estratégia

- **Não** usam PostgreSQL real — SQLite em memória, isolado e descartável.
- `conftest.py` define variáveis de ambiente **antes** de importar o app.
- `app.dependency_overrides[get_db]` substitui o banco real pelo de teste.

### Fixtures (`conftest.py`)

```
db_session  →  cria tabelas, abre UMA sessão, fecha e derruba no fim
    │
    ▼
client      →  override de get_db para devolver a MESMA sessão
```

Essa refatoração permite testes que alteram o banco diretamente (ex.: desativar usuário para testar `403`).

### Suíte de testes

| Teste | Cenário | Espera |
|-------|---------|--------|
| `test_register` | Cadastro com sucesso (sem vazar hash) | `201` |
| `test_register_email_duplicado` | E-mail repetido | `409` |
| `test_login_e_users_me` | Registra → loga → acessa `/users/me` | `200` |
| `test_login_senha_errada` | Senha incorreta | `401` |
| `test_login_email_inexistente` | E-mail não cadastrado | `401` |
| `test_users_me_sem_token` | Rota protegida sem token | `401` |
| `test_users_me_token_invalido` | Token malformado | `401` |
| `test_users_me_usuario_inativo` | Token válido, usuário inativo | `403` |
| `test_register_senha_curta` | Senha com menos de 8 caracteres | `422` |
| `test_register_email_invalido` | E-mail inválido | `422` |

### Como rodar

```bash
pytest          # todos os testes
pytest -v       # modo verboso
pytest tests/test_auth.py::test_register   # teste específico
```

Não é necessário Docker nem PostgreSQL para os testes.

---

## 10. Docker e empacotamento

### `Dockerfile`

1. Base: `python:3.12-slim`
2. Instala dependências (`requirements.txt`) — camada cacheável
3. Copia `app/`, `alembic/` e `alembic.ini`
4. `EXPOSE 8000`
5. `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`

### `docker-compose.yml`

Dois serviços:

**`db` (PostgreSQL 16):**
- Usuário/senha/banco: `app` / `app` / `appdb`
- Porta no host: `5434:5432`
- Volume persistente: `auth_api_pgdata`
- Healthcheck com `pg_isready`

**`api` (FastAPI):**
- Build a partir do `Dockerfile`
- `DATABASE_URL`: `postgresql+psycopg2://app:app@db:5432/appdb` (rede interna Docker)
- Porta: `8000:8000`
- Aguarda banco saudável (`depends_on: condition: service_healthy`)
- Comando: `alembic upgrade head && uvicorn ...`

### Comandos Docker

```bash
docker compose up --build       # sobe tudo (primeira vez)
docker compose up -d            # segundo plano
docker compose logs -f api      # acompanha logs
docker compose down             # derruba (mantém dados)
docker compose down -v          # derruba e apaga volume do banco
```

---

## 11. CI/CD

GitHub Actions (`.github/workflows/ci.yml`):

- Dispara em `push` e `pull_request`.
- Python 3.12.
- Instala `requirements.txt`.
- Executa `pytest -v`.

Os testes rodam com SQLite em memória — sem serviços externos.

---

## 12. Padrões de projeto

| Padrão / Conceito | Onde aparece | O que entrega |
|-------------------|--------------|---------------|
| **Layered Architecture** | toda a árvore `app/` | Separação de responsabilidades |
| **Dependency Injection** | `Depends(get_db)`, `Depends(get_current_user)` | Sessão e usuário injetados |
| **Service Layer** | `services/user_service.py` | Regra de negócio isolada do HTTP |
| **DTO / Schema** | `schemas/user.py` | Contratos e blindagem de dados sensíveis |
| **ORM / Data Mapper** | `models/user.py` | Classes Python ⇆ tabelas SQL |
| **Settings object** | `core/config.py` | Configuração centralizada via `.env` |
| **Migrations** | `alembic/` | Evolução reproduzível do banco |
| **Stateless Auth (JWT)** | `core/security.py` | Autenticação sem sessão no servidor |
| **Guard Dependency** | `get_current_user` | Proteção reutilizável de rotas |

---

## 13. Problemas comuns

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `connection refused` na porta 5434 | Banco não está rodando ou porta não publicada | Verifique `docker ps` e use `-p 5434:5432` |
| `password authentication failed for user "app"` | Credenciais do `.env` ≠ banco | Confira `DATABASE_URL` |
| `relation "users" does not exist` | Migrations não aplicadas | Rode `alembic upgrade head` |
| App não sobe — erro de `DATABASE_URL`/`SECRET_KEY` | Falta `.env` ou variáveis | Copie `.env.example` e preencha |
| Porta 8000 em uso | Outro processo na porta | `uvicorn app.main:app --port 8001` |
| Erro bcrypt com senha longa | Senha > 72 bytes | Use senha até 72 caracteres (validado no schema) |

---

## 14. Como rodar o projeto

Existem **dois caminhos**. Escolha um:

- **Caminho A — Docker (recomendado):** sobe banco + API juntos.
- **Caminho B — Manual:** Python local + banco no Docker.

---

### Pré-requisito: arquivo `.env`

O repositório traz `.env.example`:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5434/appdb
SECRET_KEY=coloque-uma-chave-secreta-com-pelo-menos-32-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

| Variável | Significado |
|----------|-------------|
| `DATABASE_URL` | Conexão: usuário `app`, senha `app`, host `localhost`, porta `5434`, banco `appdb` |
| `SECRET_KEY` | Chave que assina os JWT — **troque em produção** |
| `ALGORITHM` | Algoritmo de assinatura (deixe `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token em minutos |

Gerar uma `SECRET_KEY` segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> No caminho Docker, o `docker-compose.yml` injeta variáveis no container da API. Para o caminho manual, copie e edite o `.env`.

---

### Caminho A — Docker (recomendado)

**1. Instale o Docker Desktop** e confirme:

```bash
docker --version
```

**2. (Opcional) Configure `SECRET_KEY` no `.env` na raiz do projeto** — o Compose usa `${SECRET_KEY}`.

**3. Suba tudo:**

```bash
docker compose up --build
```

O que acontece:
1. Constrói a imagem da API (`Dockerfile`).
2. Sobe o PostgreSQL e aguarda healthcheck.
3. Sobe a API, roda `alembic upgrade head` e inicia o uvicorn.

**4. Acesse o Swagger:**

👉 **http://localhost:8000/docs**

---

### Caminho B — Manual (desenvolvimento local)

**1. Instale Python 3.12+:**

```bash
python --version
```

**2. Suba só o banco PostgreSQL:**

```bash
docker run -d --name pg-auth -p 5434:5432 \
  -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=appdb \
  postgres:16
```

**3. Crie e ative o ambiente virtual:**

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**4. Instale as dependências:**

```bash
pip install -r requirements.txt
```

**5. Crie o `.env`:**

```bash
cp .env.example .env
# Edite .env e troque SECRET_KEY por uma chave aleatória
```

**6. Aplique as migrations:**

```bash
alembic upgrade head
```

**7. Suba a API:**

```bash
uvicorn app.main:app --reload
```

**8. Acesse o Swagger:**

👉 **http://127.0.0.1:8000/docs**

---

### Testando no Swagger

1. **`GET /health`** → deve retornar `{"status": "ok"}`.
2. **`POST /auth/register`** → cadastre com e-mail e senha (mín. 8 caracteres). Esperado: `201`.
3. Clique em **Authorize** (cadeado) → preencha `username` (e-mail) e `password` → o Swagger obtém o JWT automaticamente.
4. **`GET /users/me`** → com autorização ativa, deve retornar `200` com seus dados.

Grupos visíveis no Swagger: `auth`, `users`, `infra`.

---

### Rodando os testes (opcional)

```bash
pytest -v
```

Não precisa de banco nem Docker.

---

### Documentação adicional

| Documento | Conteúdo |
|-----------|----------|
| [ARQUITETURA.md](../ARQUITETURA.md) | Aprofundamento técnico linha a linha |
| [docs/visao-geral.md](visao-geral.md) | Panorama da arquitetura |
| [docs/onboarding.md](onboarding.md) | Guia passo a passo para iniciantes |
| [docs/componentes/](componentes/) | Detalhe de cada camada |
| [docs/docker-compose.md](docker-compose.md) | Explicação do Compose |
| [docs/dockerfile.md](dockerfile.md) | Explicação do Dockerfile |

---

## Resumo final

```
cadastro de usuário
    ↓
hash de senha (bcrypt)
    ↓
persistência no PostgreSQL (via Alembic)
    ↓
login
    ↓
geração de JWT
    ↓
autorização via Bearer token
    ↓
acesso à rota protegida /users/me
```

A API retorna corretamente os dados do usuário autenticado e **não expõe** informações sensíveis como o hash da senha. A arquitetura em camadas torna o projeto limpo, testável e pronto para evoluir.
