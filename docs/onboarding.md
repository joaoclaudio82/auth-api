# 🚀 Onboarding — Colocando o projeto para rodar do zero

> Este guia é para **qualquer pessoa**, mesmo sem experiência prévia. Vamos do "não tenho nada instalado" até "a API está funcionando no meu navegador". Siga os passos **na ordem**.
>
> Se quiser entender *o que* o projeto faz antes de rodar, leia primeiro a [visão geral](visao-geral.md). Se quiser entender cada pasta, veja [componentes/](componentes/).

---

## 1. O que é este projeto (em 30 segundos)

É uma **API de autenticação**: um programa que roda em segundo plano e responde a pedidos pela internet/rede. Ele sabe **cadastrar** usuários, fazer **login** (devolvendo um "crachá digital" chamado **token JWT**) e dizer **quem é** o dono de um token. É escrito em Python com o framework FastAPI e guarda os dados em um banco PostgreSQL.

---

## 2. Conceitos básicos que vão aparecer

Não precisa decorar — só entender o nome quando aparecer:

| Termo | O que é, em linguagem simples |
|-------|-------------------------------|
| **Terminal / PowerShell** | A "tela preta" onde você digita comandos. No Windows, abra o **PowerShell**. |
| **Python** | A linguagem em que o projeto é escrito. Precisa estar instalada. |
| **Dependências** | Bibliotecas que o projeto usa (listadas em `requirements.txt`). |
| **Banco de dados (PostgreSQL)** | Onde os usuários ficam guardados. |
| **Docker** | Um programa que roda outros programas "em caixinhas" (containers) isoladas. Facilita subir o banco sem instalar nada. |
| **`.env`** | Um arquivo de texto com as **configurações secretas** (senha do banco, chave dos tokens). Veja a seção 4. |
| **Migration** | O "script" que cria as tabelas no banco. Roda pelo Alembic. |
| **Swagger** | Uma página web automática para testar a API clicando em botões. |

---

## 3. Escolha o seu caminho

Há **dois jeitos** de rodar o projeto. Escolha **um**:

- **🅰️ Caminho Docker (mais fácil — recomendado):** o Docker sobe o banco **e** a API juntos, já configurados. Você só precisa do Docker instalado. **Pule para a seção 5.**
- **🅱️ Caminho Manual (Python na sua máquina):** você instala o Python, sobe só o banco no Docker, e roda a API "na mão". Bom para desenvolver e mexer no código. **Vá para a seção 6.**

> 💡 Se é a sua primeira vez, use o **Caminho Docker**.

---

## 4. Entendendo o arquivo `.env` (importante para os dois caminhos)

O `.env` guarda as **configurações** do projeto. Ele **não deve ir para o Git** (contém segredos), por isso o repositório traz um modelo chamado **`.env.example`** que você copia.

Conteúdo do `.env.example`:

```bash
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5434/appdb
SECRET_KEY=coloque-uma-chave-secreta-com-pelo-menos-32-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

O que cada linha significa:

| Variável | Significado |
|----------|-------------|
| `DATABASE_URL` | Endereço de conexão com o banco. Lê-se: *driver `psycopg2`, usuário `app`, senha `app`, host `localhost`, porta `5434`, banco `appdb`*. |
| `SECRET_KEY` | A chave que **assina** os tokens. Troque por um texto longo e aleatório. **Nunca** use a de exemplo em produção. |
| `ALGORITHM` | Algoritmo de assinatura do token. Deixe `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Quantos minutos o token dura (aqui, 30). |

> ⚠️ **Por que isso importa:** o arquivo [`app/core/config.py`](componentes/core.md) **exige** `DATABASE_URL` e `SECRET_KEY`. Se faltarem, a aplicação nem inicia. Por isso criar o `.env` é um passo obrigatório no caminho manual.

> 🐳 **No caminho Docker você normalmente NÃO precisa mexer no `.env`**, porque o `docker-compose.yml` já define essas variáveis para o container da API. O `.env` é mais relevante no caminho manual.

### Como gerar uma `SECRET_KEY` boa
No PowerShell:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copie o resultado e cole no `SECRET_KEY` do seu `.env`.

---

## 5. 🅰️ Caminho Docker (recomendado)

### Passo 5.1 — Instalar o Docker
Baixe e instale o **Docker Desktop**: https://www.docker.com/products/docker-desktop/
Depois de instalar, **abra o Docker Desktop** e espere ele dizer que está "running".

Confirme no PowerShell:
```powershell
docker --version
```

### Passo 5.2 — Subir tudo
Dentro da pasta do projeto (`f:\devpleno\projeto1`), rode:
```powershell
docker compose up --build
```

O que acontece (você verá nos logs):
1. O Docker **constrói** a imagem da API a partir do [`Dockerfile`](dockerfile.md).
2. Sobe o **banco PostgreSQL** e espera ele ficar saudável.
3. Sobe a **API**, que primeiro roda as **migrations** (`alembic upgrade head`, cria a tabela `users`) e depois inicia o servidor.

> 📖 Para entender esse arquivo em detalhe, veja [docker-compose.md](docker-compose.md).

### Passo 5.3 — Abrir a API
Quando aparecer algo como `Uvicorn running on http://0.0.0.0:8000`, abra no navegador:

👉 **http://localhost:8000/docs**

Essa é a página do **Swagger**. Pule para a **seção 7** para testar.

### Comandos úteis do Docker
```powershell
docker compose up -d        # sobe em segundo plano (libera o terminal)
docker compose logs -f api  # acompanha os logs da API
docker compose down         # derruba tudo (mantém os dados do banco)
docker compose down -v      # derruba E apaga os dados do banco
```

> ℹ️ **Sobre as portas no Docker:** dentro do Docker, a API fala com o banco internamente. Para *você* acessar o banco pelo seu PC (opcional, com um cliente SQL), use `localhost:5434` (mapeada no `docker-compose.yml`). A API em si fica em `localhost:8000`.

✅ **Pronto! No caminho Docker, você terminou. Vá para a seção 7 (testar).**

---

## 6. 🅱️ Caminho Manual (Python na sua máquina)

### Passo 6.1 — Instalar o Python
Instale o **Python 3.12** (ou superior): https://www.python.org/downloads/
Na instalação, **marque a opção "Add Python to PATH"**.

Confirme:
```powershell
python --version
```

### Passo 6.2 — Subir só o banco PostgreSQL (via Docker)
A forma mais simples de ter o banco é com um container. Note a porta **`5434`** (a mesma do `.env`):
```powershell
docker run -d --name pg-auth -p 5434:5432 -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=appdb postgres:16
```
Isso cria um banco com usuário `app`, senha `app`, base `appdb`, acessível em `localhost:5434`.

> 🔌 **Sobre a porta:** todo o projeto usa a porta **5434** no host (tanto o `.env`/`.env.example` quanto o `docker-compose.yml`). Dentro do container o PostgreSQL continua na 5432 (padrão); o `5434:5432` apenas mapeia "porta no seu PC : porta no container". Só não rode os dois caminhos ao mesmo tempo, para a porta 5434 não ficar ocupada em dobro.

### Passo 6.3 — Criar e ativar um ambiente virtual
Um "ambiente virtual" isola as dependências deste projeto das do resto do seu PC.
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Se aparecer erro de permissão ao ativar, rode antes:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Quando ativo, o terminal mostra `(.venv)` no começo da linha.

### Passo 6.4 — Instalar as dependências
```powershell
pip install -r requirements.txt
```

### Passo 6.5 — Criar o arquivo `.env`
Copie o modelo (veja a [seção 4](#4-entendendo-o-arquivo-env-importante-para-os-dois-caminhos) para o significado de cada linha):
```powershell
Copy-Item .env.example .env
```
Depois edite o `.env` e troque a `SECRET_KEY` por uma chave longa e aleatória.

### Passo 6.6 — Criar as tabelas no banco (migrations)
```powershell
alembic upgrade head
```
Isso cria a tabela `users`. 📖 Detalhes em [componentes/alembic.md](componentes/alembic.md).

### Passo 6.7 — Subir a API
```powershell
uvicorn app.main:app --reload
```
O `--reload` reinicia a API sozinha quando você edita o código (ótimo para desenvolver).

### Passo 6.8 — Abrir a API
👉 **http://127.0.0.1:8000/docs**

---

## 7. Testando a API no Swagger (vale para os dois caminhos)

Abra **http://localhost:8000/docs**. Você verá os grupos `auth`, `users` e `infra`.

### 7.1 — Checar saúde
Abra `GET /health` → **Try it out** → **Execute**. Deve retornar `{"status": "ok"}`.

### 7.2 — Cadastrar um usuário
Em `POST /auth/register` → **Try it out**, preencha o corpo:
```json
{
  "email": "voce@exemplo.com",
  "password": "minhasenha123"
}
```
Clique **Execute**. Resposta esperada: **201** com `{ id, email, is_active }` — repare que a senha **não** aparece. ✅

### 7.3 — Fazer login (pegar o token)
A forma mais prática é usar o botão **Authorize** (cadeado, no topo direito):
1. Clique em **Authorize**.
2. Em `username` coloque o **e-mail** cadastrado; em `password`, a senha.
3. Clique **Authorize** e depois **Close**.

O Swagger faz o login por você e passa a enviar o token automaticamente nas próximas chamadas.

### 7.4 — Acessar a rota protegida
Abra `GET /users/me` → **Try it out** → **Execute**. Como você está autenticado, deve retornar **200** com os seus dados. Se tirar a autorização (cadeado) e tentar de novo, recebe **401**. ✅

---

## 8. Rodando os testes automatizados (opcional)

Os testes **não** precisam do banco nem do Docker — usam um banco SQLite em memória.
```powershell
pytest -v
```
📖 Como funcionam: [componentes/tests.md](componentes/tests.md).

---

## 9. Problemas comuns e soluções

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `connection refused` na porta 5434 | O banco não está rodando, ou a porta não foi publicada | Confira se o container do banco subiu (`docker ps`) e se usou `-p 5434:5432` |
| `password authentication failed for user "app"` | Usuário/senha do `.env` ≠ do banco | Garanta que `DATABASE_URL` bate com o que o banco foi criado |
| `relation "users" does not exist` | As tabelas não foram criadas | Rode `alembic upgrade head` |
| App não sobe e fala de `DATABASE_URL`/`SECRET_KEY` | Falta o `.env` ou faltam variáveis | Crie o `.env` a partir do `.env.example` (seção 4) |
| Erro ao ativar o `.venv` (PowerShell) | Política de execução | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Porta 8000 já em uso | Outro programa usa a 8000 | Rode em outra porta: `uvicorn app.main:app --port 8001` |

---

## 10. Para onde ir depois

- 🧭 **Entender a arquitetura geral:** [visao-geral.md](visao-geral.md)
- 🧩 **Entender cada componente:** [componentes/](componentes/) — [api](componentes/api.md) · [services](componentes/services.md) · [models](componentes/models.md) · [schemas](componentes/schemas.md) · [core](componentes/core.md) · [alembic](componentes/alembic.md) · [tests](componentes/tests.md)
- 🐳 **Entender o Docker:** [docker-compose.md](docker-compose.md) · [dockerfile.md](dockerfile.md)
- 📐 **Aprofundamento técnico completo:** [../ARQUITETURA.md](../ARQUITETURA.md)

Bem-vindo(a) ao projeto! 🎉
