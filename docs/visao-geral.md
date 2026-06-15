# Visão geral do projeto e arquitetura

> Documento de panorama. Para o detalhe linha-a-linha de cada componente, veja a pasta
> [`componentes/`](componentes/). Para um passo a passo de como rodar do zero, veja
> [`onboarding.md`](onboarding.md). Existe também um aprofundamento em
> [`../ARQUITETURA.md`](../ARQUITETURA.md), um [guia completo](guia-completo.md) e o
> [relatório histórico de implementação](relatorio-implementacao.md).

---

## 1. O que é o projeto

Este projeto é uma **API de autenticação de usuários**. Em poucas palavras, ela faz três coisas:

1. **Cadastrar** um usuário — `POST /auth/register`
2. **Logar** e devolver um **token JWT** — `POST /auth/login`
3. **Identificar** o dono de um token em uma **rota protegida** — `GET /users/me`

E ainda expõe um `GET /health` para verificar se o serviço está no ar.

Duas garantias de segurança são centrais:
- A senha **nunca** é guardada em texto puro — vira um **hash bcrypt** antes de tocar o banco.
- O acesso às rotas protegidas é feito por **token JWT assinado**, com validade (expiração).

### Stack

**FastAPI** (web) · **PostgreSQL** (banco) · **SQLAlchemy 2.0** (ORM) · **Alembic** (migrations) · **Pydantic v2** (validação/config) · **python-jose** (JWT) · **passlib/bcrypt** (hash) · **pytest** (testes) · **Docker** (empacotamento).

---

## 2. A grande ideia: Arquitetura em Camadas

O coração do projeto é a **separação de responsabilidades**. Em vez de jogar tudo dentro das rotas, cada tipo de trabalho mora em uma camada própria. Isso é a **arquitetura em camadas** (*layered architecture*).

```
        CLIENTE (Swagger, curl, front-end)
                    │ HTTP (JSON / form)
                    ▼
┌───────────────────────────────────────────────────────┐
│  CAMADA 1 — API / ROTAS         app/api/                │  ← só HTTP
│  recebe request · valida entrada · decide status code   │
└───────────────────────────┬─────────────────────────────┘
                            │ chama funções Python puras
                            ▼
┌───────────────────────────────────────────────────────┐
│  CAMADA 2 — SERVICES            app/services/           │  ← regra de negócio
│  "email é único?" · "senha bate com o hash?"            │
└───────────────────────────┬─────────────────────────────┘
                            │ usa o ORM
                            ▼
┌───────────────────────────────────────────────────────┐
│  CAMADA 3 — MODELS              app/models/             │  ← mapeia classes ⇆ tabelas
└───────────────────────────┬─────────────────────────────┘
                            │ SQL via engine
                            ▼
              BANCO DE DADOS — PostgreSQL

   Camadas de apoio (transversais, usadas por todas):
   app/core/    → config (.env), database (sessão), security (hash + JWT)
   app/schemas/ → contratos Pydantic de entrada e saída
   alembic/     → versionamento/migração do banco
   tests/       → testes automatizados
```

> 💡 **Regra de ouro:** a dependência aponta sempre **para baixo** — Rota → Serviço → Model → Banco. Nunca o contrário. O serviço não sabe que existe HTTP; o model não sabe que existe Pydantic.

### Por que separar em camadas?

| Benefício | Como a separação ajuda |
|-----------|------------------------|
| **Manutenção** | Mudou a regra de negócio? Mexe só em `services/`. Mudou a resposta HTTP? Só em `api/`. |
| **Testabilidade** | Dá pra testar a regra de negócio sem subir o FastAPI inteiro. |
| **Reuso** | A mesma função `create_user()` serve a vários endpoints. |
| **Baixo acoplamento** | Trocar o protocolo, o banco ou o framework afeta poucas camadas. |

---

## 3. Mapa das pastas

```text
projeto1/
├── app/
│   ├── main.py            # ponto de entrada: cria o app e registra os routers
│   ├── api/               # CAMADA 1 — rotas HTTP          → componentes/api.md
│   ├── services/          # CAMADA 2 — regra de negócio    → componentes/services.md
│   ├── models/            # CAMADA 3 — modelos ORM          → componentes/models.md
│   ├── schemas/           # contratos Pydantic (entrada/saída) → componentes/schemas.md
│   └── core/              # config, database, security      → componentes/core.md
├── alembic/               # migrations do banco             → componentes/alembic.md
├── tests/                 # testes automatizados            → componentes/tests.md
├── docker-compose.yml     # orquestra API + PostgreSQL      → docker-compose.md
├── Dockerfile             # constrói a imagem da API        → dockerfile.md
├── requirements.txt       # dependências Python
├── .env                   # variáveis de ambiente (segredos — não versionar)
└── docs/                  # esta documentação
```

Cada pasta tem um documento dedicado em [`componentes/`](componentes/) explicando-a em detalhe.

---

## 4. Os três fluxos principais

### 🟢 Cadastro — `POST /auth/register`
```
Cliente envia { email, password }
 → [api/auth] valida com UserCreate e pergunta ao serviço "email já existe?"
 → se existe   → 409 "E-mail já cadastrado"
 → se não      → [services] create_user: gera hash bcrypt, salva no banco
 → resposta filtrada por UserRead (sem o hash!)
 → Cliente recebe 201 { id, email, is_active }
```

### 🔵 Login — `POST /auth/login`
```
Cliente envia form { username=email, password }
 → [api/auth] chama authenticate
 → [services] busca por email e compara a senha com o hash
 → inválido → 401 "Credenciais inválidas"
 → válido   → gera JWT { sub: email, exp: agora+30min } assinado com a secret_key
 → Cliente recebe 200 { access_token, token_type: "bearer" }
```

### 🟣 Rota protegida — `GET /users/me`
```
Cliente envia header Authorization: Bearer <JWT>
 → [api/users] extrai o token e chama get_current_user
 → decode_token valida assinatura + expiração → extrai o email
 → busca o usuário; confere se está ativo
 → falha → 401 (token/usuário) ou 403 (inativo)
 → ok    → 200 { id, email, is_active }
```

---

## 5. Padrões de projeto presentes

| Padrão / Conceito | Onde aparece | O que entrega |
|-------------------|--------------|---------------|
| **Layered Architecture** | toda a árvore `app/` | Separação de responsabilidades |
| **Dependency Injection** | `Depends(get_db)`, `Depends(get_current_user)` | Sessão e usuário injetados automaticamente |
| **Service Layer** | `services/` | Regra de negócio isolada do HTTP |
| **DTO / Schema** | `schemas/` (Pydantic) | Contratos e blindagem de dados sensíveis |
| **ORM / Data Mapper** | `models/` (SQLAlchemy) | Classes Python ⇆ tabelas SQL |
| **Settings object** | `core/config.py` | Configuração centralizada via `.env` |
| **Migrations** | `alembic/` | Evolução reproduzível do banco |
| **Stateless Auth (JWT)** | `core/security.py` | Autenticação sem sessão no servidor |
| **Guard Dependency** | `get_current_user` | Proteção reutilizável de rotas |

---

## 6. Resumo em uma frase

> **Cada arquivo tem um único motivo para mudar.** As rotas só cuidam de HTTP, os serviços só de regra de negócio, os models só descrevem o banco, os schemas só definem contratos, e o `core/` concentra a infraestrutura. É essa disciplina que torna a API limpa, testável e pronta para crescer.

---

### Próximos passos
- Para **colocar o projeto pra rodar** do zero, mesmo sem experiência: [`onboarding.md`](onboarding.md).
- Para entender **um componente específico**: pasta [`componentes/`](componentes/).
- Para o **aprofundamento técnico completo**: [`../ARQUITETURA.md`](../ARQUITETURA.md).
- Para **tudo consolidado**: [`guia-completo.md`](guia-completo.md).
- Para o **relatório histórico** (Swagger manual, troubleshooting): [`relatorio-implementacao.md`](relatorio-implementacao.md).
- Índice geral: [`README.md`](README.md).
