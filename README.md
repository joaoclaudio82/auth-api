# Auth API

API de autenticação de usuários com **FastAPI**, **PostgreSQL**, **SQLAlchemy**, **Alembic**, **JWT** e **bcrypt**.

Cadastro, login com token JWT e rota protegida para identificar o usuário autenticado. Senhas nunca são armazenadas em texto puro.

## Stack

FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Pydantic v2 · python-jose · passlib/bcrypt · pytest · Docker

## Arquitetura

Camadas separadas: `api/` (HTTP) → `services/` (regra de negócio) → `models/` (ORM), com apoio em `core/`, `schemas/` e `alembic/`.

Detalhes em [ARQUITETURA.md](ARQUITETURA.md) e [docs/visao-geral.md](docs/visao-geral.md).

## Endpoints

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/health` | Healthcheck |
| `POST` | `/auth/register` | Cadastro de usuário |
| `POST` | `/auth/login` | Login (retorna JWT) |
| `GET` | `/users/me` | Dados do usuário autenticado |

Documentação interativa: `/docs` (Swagger).

## Como rodar

### Docker (recomendado)

```bash
docker compose up --build
```

- API: http://localhost:8001/docs
- PostgreSQL: `localhost:5434`

As migrations rodam automaticamente no start do container.

### Manual (desenvolvimento local)

```bash
# 1. Banco PostgreSQL
docker run -d --name pg-auth -p 5434:5432 \
  -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=appdb postgres:16

# 2. Ambiente Python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuração
cp .env.example .env
# Edite SECRET_KEY (mínimo 32 caracteres)

# 4. Migrations e API
alembic upgrade head
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000/docs

Guia completo: [docs/onboarding.md](docs/onboarding.md)

## Testes

```bash
pytest -v
```

Não é necessário Docker nem PostgreSQL — os testes usam SQLite em memória.

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DATABASE_URL` | Sim | Conexão com PostgreSQL |
| `SECRET_KEY` | Sim | Chave de assinatura JWT (≥ 32 chars) |
| `ALGORITHM` | Não | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Não | Default: `30` |

Modelo: [.env.example](.env.example)

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [docs/README.md](docs/README.md) | Índice de toda a documentação |
| [docs/onboarding.md](docs/onboarding.md) | Passo a passo para iniciantes |
| [docs/guia-completo.md](docs/guia-completo.md) | Documentação consolidada |
| [docs/relatorio-implementacao.md](docs/relatorio-implementacao.md) | Relatório histórico da implementação |
| [docs/componentes/](docs/componentes/) | Detalhe de cada camada |
| [ARQUITETURA.md](ARQUITETURA.md) | Aprofundamento técnico |
| [afazer.md](afazer.md) | Roadmap de evolução do projeto |

## Estrutura

```text
app/
├── api/          # rotas HTTP
├── services/     # regra de negócio
├── models/       # ORM
├── schemas/      # contratos Pydantic
└── core/         # config, database, security
alembic/          # migrations
tests/            # pytest
```
