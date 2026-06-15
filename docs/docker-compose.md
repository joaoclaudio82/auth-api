# Explicação do docker-compose.yml

Este documento explica, de forma didática, o `docker-compose.yml` do projeto.

O **Docker Compose** permite descrever e subir vários containers juntos com um único comando. Em vez de rodar cada container na mão, você declara tudo em um arquivo e o Compose cuida de construir, conectar e iniciar os serviços na ordem certa.

```yaml
services:
  db:
    image: postgres:16
    container_name: auth-api-db
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: appdb
    ports:
      - "5434:5432"
    volumes:
      - auth_api_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d appdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: auth-api
    environment:
      DATABASE_URL: postgresql+psycopg2://app:app@db:5432/appdb
      SECRET_KEY: troque-em-producao
      ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  auth_api_pgdata:
```

---

## Visão geral

O arquivo tem 3 blocos principais:

- **`services:`** → os containers que vão rodar (`db` e `api`).
- **`volumes:`** → armazenamento que sobrevive aos containers.
- Não há bloco `networks`, então o Compose cria uma **rede padrão** automaticamente, onde os serviços se enxergam pelo **nome do serviço**.

---

## Serviço `db` (banco PostgreSQL)

```yaml
db:
  image: postgres:16
  container_name: auth-api-db
  environment:
    POSTGRES_USER: app
    POSTGRES_PASSWORD: app
    POSTGRES_DB: appdb
  ports:
    - "5434:5432"
  volumes:
    - auth_api_pgdata:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U app -d appdb"]
    interval: 5s
    timeout: 5s
    retries: 5
```

### `image: postgres:16`
Usa a imagem oficial do **PostgreSQL 16** pronta do Docker Hub. Aqui não construímos nada — apenas baixamos uma imagem pronta.

### `container_name: auth-api-db`
Define um nome fixo para o container (em vez do nome aleatório que o Docker geraria).

### `environment`
Variáveis que o Postgres usa na **primeira inicialização** para se configurar:
- `POSTGRES_USER: app` → cria o usuário `app`.
- `POSTGRES_PASSWORD: app` → com a senha `app`.
- `POSTGRES_DB: appdb` → e o banco de dados `appdb`.

### `ports: "5434:5432"`
O formato é `porta_do_seu_PC : porta_dentro_do_container`.
- Dentro do container, o Postgres escuta na `5432` (padrão).
- Na sua máquina, ele aparece na `5434`.
- Ou seja, do seu PC você se conecta em `localhost:5434`. Provavelmente usaram `5434` para **não conflitar** com um Postgres já instalado localmente na `5432`.

### `volumes: auth_api_pgdata:/var/lib/postgresql/data`
Os dados do Postgres ficam guardados no volume `auth_api_pgdata`.
- 💡 Sem isso, se o container fosse removido, **você perderia o banco inteiro**. O volume persiste os dados de forma independente do ciclo de vida do container.

### `healthcheck`
A cada 5 segundos roda `pg_isready` para perguntar "o banco já está pronto para aceitar conexões?". Tenta até 5 vezes.
- Isso é importante por causa do `depends_on` da API (explicado abaixo): a API só sobe quando o banco estiver realmente saudável.

---

## Serviço `api` (aplicação FastAPI)

```yaml
api:
  build: .
  container_name: auth-api
  environment:
    DATABASE_URL: postgresql+psycopg2://app:app@db:5432/appdb
    SECRET_KEY: troque-em-producao
    ALGORITHM: HS256
    ACCESS_TOKEN_EXPIRE_MINUTES: 30
  ports:
    - "8000:8000"
  depends_on:
    db:
      condition: service_healthy
  command: >
    sh -c "alembic upgrade head &&
           uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

### `build: .`
Diferente do `db`, aqui a imagem é **construída** a partir do `Dockerfile` que está na pasta atual (`.`).

### `environment`
Variáveis de configuração da API:
- `DATABASE_URL` → a string de conexão com o banco. **Repare no `@db:5432`**: o `db` ali é exatamente o nome do serviço do banco. Dentro da rede do Compose, um container acessa o outro pelo nome do serviço. E note que aqui é a porta **`5432`** (interna), **não** a `5434` — pois a comunicação acontece dentro da rede do Docker, sem passar pela sua máquina.
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` → configurações de autenticação/JWT da aplicação.

### `ports: "8000:8000"`
A API fica acessível em `localhost:8000` no seu navegador.

### `depends_on` com `condition: service_healthy`
A API só inicia **depois** que o `healthcheck` do banco passar.
- Sem isso, a API poderia subir antes do Postgres estar pronto e quebrar ao tentar conectar. É por isso que o `healthcheck` do `db` existe.

### `command`
Sobrescreve o comando de inicialização da imagem. Ele faz duas coisas em sequência:
1. `alembic upgrade head` → aplica as **migrations** (cria/atualiza as tabelas no banco).
2. `&&` → só se o passo 1 der certo, então...
3. `uvicorn app.main:app --host 0.0.0.0 --port 8000` → sobe o servidor web da API.

O `--host 0.0.0.0` é essencial em container: faz o servidor escutar em todas as interfaces, senão o mapeamento de porta não funcionaria.

---

## O bloco `volumes`

```yaml
volumes:
  auth_api_pgdata:
```
Apenas **declara** o volume nomeado que o serviço `db` utiliza. O Docker gerencia onde ele fica fisicamente no disco.

---

## Como isso funciona na prática

Quando você roda `docker compose up`:

1. O Docker constrói a imagem da `api` (a partir do Dockerfile).
2. Sobe o container `db` e fica testando o healthcheck.
3. Quando o `db` fica saudável, sobe a `api`.
4. A `api` roda as migrations e inicia o uvicorn.
5. Você acessa a API em `localhost:8000` e o banco (se precisar) em `localhost:5434`.

### Comandos úteis

| Comando | O que faz |
|---|---|
| `docker compose up -d` | Sobe tudo em segundo plano |
| `docker compose logs -f api` | Acompanha os logs da API em tempo real |
| `docker compose ps` | Lista os containers e seu status |
| `docker compose down` | Derruba tudo, mas **mantém** o volume/dados |
| `docker compose down -v` | Derruba **e apaga** o volume (perde o banco) |

---

## ⚠️ Atenção para produção

- A `SECRET_KEY: troque-em-producao` e a senha do banco (`app`/`app`) estão fixas no arquivo. Para desenvolvimento tudo bem, mas em produção o ideal é mover esses valores para um arquivo `.env` (e nunca commitá-lo). O próprio nome do valor já avisa isso. 😄

## Relação com o Dockerfile

- O `build: .` faz o Compose construir a imagem da API usando o `Dockerfile` do projeto (veja [dockerfile.md](dockerfile.md)).
- O `command:` do Compose sobrescreve o `CMD` do Dockerfile para também rodar as migrations no start.
- A porta `8000` declarada no `EXPOSE` do Dockerfile é efetivamente publicada pelo `ports: "8000:8000"` daqui.
