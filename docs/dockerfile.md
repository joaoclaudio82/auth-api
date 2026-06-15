# Explicação do Dockerfile

Este documento explica, de forma didática, o `Dockerfile` que constrói a imagem da API.

Um **Dockerfile** é uma receita: cada linha é uma instrução que o Docker executa em ordem para montar a imagem da aplicação. Cada instrução cria uma "camada" (layer), e o Docker reaproveita camadas que não mudaram — por isso a **ordem das instruções importa** para o desempenho do build.

```dockerfile
FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Linha a linha

### `FROM python:3.12-slim`
Define a **imagem base**: partimos de uma imagem oficial que já tem o Python 3.12 instalado.

- O sufixo **`slim`** é uma versão enxuta da imagem (sem ferramentas e pacotes desnecessários), o que deixa a imagem final menor e mais rápida de baixar.
- Toda imagem é construída "em cima" de outra; aqui é o nosso ponto de partida.

### `WORKDIR /code`
Define o **diretório de trabalho** dentro do container. A partir daqui, todos os comandos (`COPY`, `RUN`, `CMD`) acontecem dentro de `/code`.

- É o equivalente a um `cd /code`, mas também **cria** a pasta caso ela não exista.

### `COPY requirements.txt .`
Copia **apenas** o arquivo `requirements.txt` da sua máquina para o diretório atual do container (`/code`).

- 💡 **Por que copiar só esse arquivo primeiro?** Por causa do **cache de camadas**. As dependências mudam raramente; o código-fonte muda toda hora. Ao copiar e instalar as dependências antes do código, o Docker só refaz a instalação (passo lento) quando o `requirements.txt` muda. Se você altera só o código, o Docker reaproveita a camada de dependências já instaladas. Isso acelera muito os builds do dia a dia.

### `RUN pip install --no-cache-dir -r requirements.txt`
Instala as bibliotecas Python listadas no `requirements.txt`.

- **`--no-cache-dir`**: impede o pip de guardar o cache de download dentro da imagem. Como esse cache não serve para nada em runtime, removê-lo deixa a **imagem final menor**.

### `COPY app ./app`, `COPY alembic ./alembic`, `COPY alembic.ini .`
Agora sim copiamos o **código da aplicação** para dentro da imagem:

- `app` → o código da API (FastAPI).
- `alembic` + `alembic.ini` → os arquivos de **migrations** do banco de dados (usados pelo comando `alembic upgrade head`).

Como esses arquivos mudam com frequência, ficam por último — qualquer alteração aqui só invalida o cache destas camadas, não o da instalação de dependências.

### `EXPOSE 8000`
**Documenta** que a aplicação escuta na porta `8000` dentro do container.

- ⚠️ Importante: o `EXPOSE` é apenas informativo. Ele **não** publica a porta para a sua máquina — quem faz isso é o mapeamento `ports:` no `docker-compose.yml` (`"8000:8000"`).

### `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
Define o **comando padrão** executado quando o container inicia: sobe o servidor web `uvicorn` rodando a aplicação FastAPI (`app.main:app`).

- **`--host 0.0.0.0`**: faz o servidor escutar em todas as interfaces de rede. É essencial dentro de um container — sem isso, o mapeamento de portas não funcionaria e a API ficaria inacessível de fora.
- Esse `CMD` é o comportamento **padrão** da imagem, mas pode ser **sobrescrito**. No `docker-compose.yml` deste projeto, por exemplo, o `command:` substitui este `CMD` para rodar as migrations (`alembic upgrade head`) antes de subir o uvicorn.

---

## Resumo do fluxo de build

1. Parte do Python 3.12 slim.
2. Entra na pasta `/code`.
3. Copia e instala as dependências (camada cacheável).
4. Copia o código da aplicação e as migrations.
5. Anuncia a porta 8000.
6. Define o comando que inicia a API.

## Relação com o `docker-compose.yml`

- O `docker-compose.yml` usa `build: .`, ou seja, ele constrói a imagem a partir **deste** Dockerfile.
- O `command:` do Compose sobrescreve o `CMD` daqui para também aplicar as migrations no start.
- A porta `8000` declarada no `EXPOSE` é efetivamente publicada pelo `ports: "8000:8000"` do Compose.
