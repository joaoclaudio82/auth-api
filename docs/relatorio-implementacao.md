# Relatório de Implementação — Auth API

> Documento histórico do README original do projeto (passo a passo da implementação,
> testes manuais no Swagger e problemas encontrados).
>
> Para documentação atual, comece por [README.md](../README.md) ou o [índice de docs](README.md).
> Aprofundamento técnico: [ARQUITETURA.md](../ARQUITETURA.md).

---

## Arquitetura

O projeto utiliza uma arquitetura em camadas, separando responsabilidades entre rotas HTTP, regras de negócio, modelos de banco, schemas de validação e infraestrutura base.

- `api/`: camada de entrada HTTP, responsável pelas rotas FastAPI.
- `services/`: camada de regras de negócio da aplicação.
- `models/`: modelos ORM SQLAlchemy que representam as tabelas do banco.
- `schemas/`: contratos Pydantic de entrada e saída da API.
- `core/`: configurações, conexão com banco e segurança.

Essa separação facilita manutenção, testes, evolução do código e evita concentração de lógica nas rotas.


# Relatório de Implementação — Auth API com FastAPI, PostgreSQL, SQLAlchemy, Alembic e JWT

## 1. Visão geral do projeto

Este projeto implementa uma API de autenticação de usuários utilizando **FastAPI** como framework web, **PostgreSQL** como banco de dados, **SQLAlchemy** como ORM, **Alembic** para controle de versões do banco de dados, **Pydantic** para validação de dados, **bcrypt/passlib** para hash de senhas e **JWT** para autenticação baseada em token.

O objetivo foi construir uma base profissional de autenticação, contendo:

* cadastro de usuários;
* armazenamento seguro de senha com hash;
* login com validação de credenciais;
* geração de token JWT;
* rota protegida para consultar o usuário autenticado;
* banco PostgreSQL rodando via Docker;
* criação da tabela `users` via migration com Alembic;
* testes manuais via Swagger UI.

---

## 2. Estrutura do app

A aplicação foi organizada em uma arquitetura em camadas, separando responsabilidades entre rotas, regras de negócio, modelos de banco, schemas de validação e configurações centrais.

Estrutura principal:

```text
projeto1/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── users.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   └── services/
│       ├── __init__.py
│       └── user_service.py
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── requirements.txt
└── .env
```

### 2.1 `app/main.py`

Arquivo principal da aplicação FastAPI.

Responsabilidades:

* criar a instância da aplicação;
* registrar os routers de autenticação e usuários;
* disponibilizar a rota `/health`.

Rotas registradas:

```text
GET  /health
POST /auth/register
POST /auth/login
GET  /users/me
```

---

### 2.2 `app/api/auth.py`

Arquivo responsável pelas rotas de autenticação.

Implementamos:

```text
POST /auth/register
POST /auth/login
```

A rota `/auth/register` cria um novo usuário no banco.

A rota `/auth/login` autentica o usuário e retorna um token JWT.

---

### 2.3 `app/api/users.py`

Arquivo responsável pelas rotas relacionadas ao recurso usuário.

Implementamos:

```text
GET /users/me
```

Essa rota é protegida. Ela exige um token JWT válido no header `Authorization`.

---

### 2.4 `app/core/config.py`

Arquivo responsável pelas configurações da aplicação.

Nele foram centralizadas variáveis como:

```text
DATABASE_URL
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
```

Essas configurações são lidas a partir do arquivo `.env`.

---

### 2.5 `app/core/database.py`

Arquivo responsável pela configuração do banco de dados.

Nele foram definidos:

* engine do SQLAlchemy;
* sessão do banco;
* classe `Base`;
* função `get_db`.

A função `get_db` é usada como dependência nas rotas para abrir e fechar uma sessão com o banco durante cada requisição.

---

### 2.6 `app/core/security.py`

Arquivo responsável pelas funções de segurança.

Foram implementadas funções para:

* gerar hash de senha;
* verificar senha;
* criar token JWT;
* decodificar token JWT.

Principais funções:

```python
get_password_hash()
verify_password()
create_access_token()
decode_token()
```

---

### 2.7 `app/models/user.py`

Arquivo que define o modelo SQLAlchemy da tabela `users`.

O model `User` representa a tabela de usuários no PostgreSQL.

Campos principais:

```text
id
email
hashed_password
is_active
created_at
```

O campo `hashed_password` armazena o hash da senha, nunca a senha em texto puro.

---

### 2.8 `app/schemas/user.py`

Arquivo responsável pelos schemas Pydantic.

Foram criados schemas para:

* entrada de dados no cadastro;
* saída segura dos dados do usuário;
* resposta do token.

Schemas principais:

```python
UserCreate
UserRead
Token
```

O schema `UserRead` não expõe o campo `hashed_password`, garantindo que o hash da senha não apareça nas respostas da API.

---

### 2.9 `app/services/user_service.py`

Arquivo responsável pela regra de negócio relacionada aos usuários.

Foram implementadas funções para:

```python
get_by_email()
create_user()
authenticate()
```

Essa camada separa a lógica de negócio da camada de rotas HTTP.

---

## 3. Passo a passo da implementação

### 3.1 Criação da estrutura inicial

A primeira etapa foi criar a estrutura de pastas da aplicação, separando o código em camadas:

```text
api
core
models
schemas
services
```

Essa separação facilita manutenção, testes e evolução do projeto.

---

### 3.2 Criação da aplicação FastAPI

Foi criado o arquivo `main.py` com a instância principal da aplicação:

```python
app = FastAPI(title="auth-api-fast", version="1.0.0")
```

Também foi criada a rota de saúde:

```text
GET /health
```

Essa rota serve para verificar se a aplicação está rodando corretamente.

---

### 3.3 Configuração do banco de dados

Foi configurada a conexão com PostgreSQL usando SQLAlchemy.

A aplicação passou a utilizar uma `DATABASE_URL` no seguinte formato:

```text
postgresql+psycopg2://app:app@localhost:5434/appdb
```

O PostgreSQL foi executado via Docker, com usuário `app`, senha `app`, banco `appdb` e porta local `5434`.

---

### 3.4 Criação do model `User`

Foi criado o model `User`, representando a tabela `users`.

Esse model define a estrutura esperada da tabela de usuários, incluindo:

* identificador;
* e-mail único;
* senha com hash;
* status ativo;
* data de criação.

---

### 3.5 Criação dos schemas Pydantic

Foram criados schemas para validar entrada e saída de dados.

O schema `UserCreate` recebe:

```text
email
password
```

O schema `UserRead` retorna:

```text
id
email
is_active
```

O schema `Token` retorna:

```text
access_token
token_type
```

Essa separação evita que dados sensíveis, como `hashed_password`, sejam expostos pela API.

---

### 3.6 Implementação da segurança com bcrypt e JWT

Foi implementado o hash de senha com `passlib` e `bcrypt`.

No cadastro, a senha enviada pelo usuário é transformada em hash antes de ser salva.

No login, a senha enviada é comparada com o hash salvo no banco.

Também foi implementada a geração de token JWT. O token contém o e-mail do usuário no campo `sub` e uma data de expiração no campo `exp`.

---

### 3.7 Implementação do serviço de usuário

Foi criado o arquivo `user_service.py`.

Nele foram implementadas as regras principais:

* buscar usuário por e-mail;
* criar usuário com senha hasheada;
* autenticar usuário comparando senha com hash.

Essa camada evita que as rotas tenham lógica de banco e regra de negócio misturadas.

---

### 3.8 Implementação das rotas de autenticação

No arquivo `auth.py`, foram criadas duas rotas:

```text
POST /auth/register
POST /auth/login
```

A rota `/auth/register` cadastra o usuário.

A rota `/auth/login` recebe `username` e `password`, autentica o usuário e retorna um JWT.

---

### 3.9 Implementação da rota protegida

No arquivo `users.py`, foi criada a rota:

```text
GET /users/me
```

Essa rota usa `OAuth2PasswordBearer` para ler o token enviado no header `Authorization`.

O fluxo da rota protegida é:

```text
recebe token
↓
decodifica JWT
↓
extrai e-mail do usuário
↓
busca usuário no banco
↓
retorna dados do usuário autenticado
```

---

### 3.10 Configuração do Alembic

Foi configurado o Alembic para versionar o banco de dados.

O arquivo `alembic/env.py` foi ajustado para usar:

```python
target_metadata = Base.metadata
```

Isso permite que o Alembic enxergue os models SQLAlchemy e gere migrations automaticamente.

Também foi configurado para usar a mesma `DATABASE_URL` da aplicação.

---

### 3.11 Criação da migration da tabela `users`

Foi gerada uma migration com o comando:

```bash
alembic revision --autogenerate -m "create users table"
```

Depois, a migration foi aplicada com:

```bash
alembic upgrade head
```

A aplicação criou no PostgreSQL as tabelas:

```text
alembic_version
users
```

A tabela `alembic_version` é usada pelo Alembic para controlar qual migration já foi aplicada.

---

## 4. O que foi implementado

### 4.1 Cadastro de usuários

Foi implementado o endpoint:

```text
POST /auth/register
```

Esse endpoint recebe e-mail e senha, valida os dados, verifica se o usuário já existe e salva o novo usuário no banco.

A senha não é salva diretamente. Antes de persistir o usuário, a senha é transformada em hash.

Resposta esperada:

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true
}
```

---

### 4.2 Hash de senha

A senha do usuário é protegida com bcrypt.

O fluxo é:

```text
senha recebida
↓
bcrypt gera hash
↓
hash é salvo no banco
```

Isso evita armazenar senha em texto puro.

---

### 4.3 Login de usuário

Foi implementado o endpoint:

```text
POST /auth/login
```

Esse endpoint recebe as credenciais no formato de formulário OAuth2:

```text
username
password
```

No projeto, o campo `username` representa o e-mail do usuário.

Se as credenciais estiverem corretas, a API retorna um token JWT.

Resposta esperada:

```json
{
  "access_token": "token_jwt",
  "token_type": "bearer"
}
```

---

### 4.4 Geração de JWT

O token JWT é gerado no login.

Ele contém:

```text
sub: e-mail do usuário
exp: data de expiração
```

Esse token é usado para acessar rotas protegidas.

---

### 4.5 Rota protegida `/users/me`

Foi implementada a rota:

```text
GET /users/me
```

Essa rota exige autenticação via token Bearer.

Ela retorna os dados do usuário autenticado:

```json
{
  "id": 2,
  "email": "joaoclaudio82@gmail.com",
  "is_active": true
}
```

---

### 4.6 Banco PostgreSQL via Docker

O banco foi executado em container Docker.

A aplicação acessa o banco pela porta local `5434`.

Foi necessário corrigir a publicação da porta do container para que o FastAPI, rodando fora do Docker, conseguisse acessar o PostgreSQL.

---

### 4.7 Migration com Alembic

A tabela `users` foi criada por migration, não manualmente.

Isso permite versionar o banco de dados e reproduzir a mesma estrutura em outros ambientes.

As tabelas confirmadas no PostgreSQL foram:

```text
alembic_version
users
```

---

## 5. Testes feitos no Swagger

Os testes foram realizados pela interface automática do FastAPI:

```text
http://127.0.0.1:8000/docs
```

---

### 5.1 Teste da documentação Swagger

Foi acessada a rota:

```text
GET /docs
```

Resultado:

```text
200 OK
```

A documentação da API abriu corretamente, exibindo os grupos:

```text
auth
users
infra
```

---

### 5.2 Teste da rota de cadastro

Endpoint testado:

```text
POST /auth/register
```

Entrada usada:

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

Resultado obtido:

```text
201 Created
```

Resposta obtida:

```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true
}
```

Também foi realizado cadastro com outro e-mail, retornando novamente `201 Created`.

Esse teste confirmou que:

* a API recebeu o JSON;
* o Pydantic validou os dados;
* a senha foi processada;
* o usuário foi salvo no PostgreSQL;
* a resposta não expôs `hashed_password`.

---

### 5.3 Teste da rota de login

Endpoint testado:

```text
POST /auth/login
```

Formato usado:

```text
form-data
```

Campos preenchidos:

```text
username: e-mail cadastrado
password: senha cadastrada
```

Resultado esperado e obtido:

```text
200 OK
```

Resposta obtida:

```json
{
  "access_token": "token_jwt",
  "token_type": "bearer"
}
```

Esse teste confirmou que:

* o usuário foi encontrado no banco;
* a senha enviada foi comparada com o hash salvo;
* o login foi validado;
* o token JWT foi gerado.

---

### 5.4 Teste de autorização no Swagger

Foi utilizado o botão:

```text
Authorize
```

No formulário de autorização, foram preenchidos:

```text
username: e-mail cadastrado
password: senha cadastrada
```

O Swagger chamou automaticamente o endpoint `/auth/login`, recebeu o token JWT e passou a enviar o header:

```http
Authorization: Bearer <token>
```

---

### 5.5 Teste da rota protegida

Endpoint testado:

```text
GET /users/me
```

Resultado obtido:

```text
200 OK
```

Resposta obtida:

```json
{
  "id": 2,
  "email": "joaoclaudio82@gmail.com",
  "is_active": true
}
```

Esse teste confirmou que:

* a rota estava protegida;
* o Swagger enviou o token JWT no header;
* o token foi validado;
* a API identificou o usuário autenticado;
* os dados do usuário foram retornados corretamente;
* o campo `hashed_password` não foi exposto.

---

## 6. Problemas encontrados e soluções aplicadas

### 6.1 Erro de senha no PostgreSQL

Erro inicial:

```text
password authentication failed for user "app"
```

Causa:

A aplicação tentava conectar com usuário e senha diferentes dos configurados no PostgreSQL.

Solução:

Foi ajustada a configuração do banco e recriado o container PostgreSQL com as credenciais corretas.

---

### 6.2 Porta do PostgreSQL não publicada

Erro encontrado:

```text
connection refused on port 5434
```

Causa:

O container `pg-auth` estava rodando, mas sem a porta publicada para o Windows.

Solução:

O container foi recriado com:

```bash
-p 5434:5432
```

Assim, a aplicação passou a acessar o PostgreSQL em:

```text
localhost:5434
```

---

### 6.3 Tabela `users` inexistente

Erro encontrado:

```text
relation "users" does not exist
```

Causa:

O model `User` existia no código, mas a tabela ainda não havia sido criada no PostgreSQL.

Solução:

Foi configurado o Alembic, gerada a migration e aplicada com:

```bash
alembic upgrade head
```

---

### 6.4 Ajuste no bcrypt

Foi identificado erro relacionado ao tamanho da senha no bcrypt.

Solução:

Foi usada uma senha compatível com o limite do bcrypt e sugerida validação no schema `UserCreate` para limitar o tamanho da senha.

---

## 7. Resultado final

Ao final da implementação, a API possui o fluxo completo de autenticação funcionando:

```text
cadastro de usuário
↓
hash de senha
↓
persistência no PostgreSQL
↓
login
↓
geração de JWT
↓
autorização via Swagger
↓
acesso à rota protegida /users/me
```

A API retorna corretamente os dados do usuário autenticado e não expõe informações sensíveis, como o hash da senha.

---

## 8. Conclusão

A implementação representa uma base sólida de backend profissional com FastAPI.

Foram aplicados conceitos importantes de desenvolvimento pleno, incluindo:

* arquitetura em camadas;
* separação entre rotas, serviços, schemas, models e core;
* autenticação com JWT;
* hash seguro de senha;
* integração com PostgreSQL;
* uso de Docker;
* migrations com Alembic;
* documentação automática com Swagger;
* teste manual de endpoints;
* rota protegida por token Bearer.

O projeto agora está pronto para a próxima etapa: criação de testes automatizados com Pytest, cobrindo cadastro, login, acesso à rota protegida e cenários de erro.

