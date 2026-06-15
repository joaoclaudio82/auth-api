# Componente `schemas/` — Contratos de dados (Pydantic)

> Pasta: [`app/schemas/`](../../app/schemas/)
> Arquivo: `user.py`

A camada `schemas/` define os **contratos** de dados que **entram** e **saem** da API. São classes Pydantic que validam, convertem e filtram dados. É a fronteira entre o "mundo de fora" (JSON do cliente) e o "mundo de dentro" (objetos Python/ORM).

> 🧩 **Schema ≠ Model.** O **model** ([models.md](models.md)) descreve a **tabela do banco**. O **schema** descreve o **formato dos dados na API**. Eles têm campos parecidos, mas papéis diferentes — e é proposital que sejam separados (ex.: o schema de saída esconde a senha).

---

## `user.py` — Os três contratos

```python
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class UserCreate(BaseModel):                 # ENTRADA do cadastro
    email: EmailStr
    password: str = Field(min_length=8, max_length=72,
                          description="Senha entre 8 e 72 caracteres")

class UserRead(BaseModel):                   # SAÍDA segura
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    is_active: bool

class Token(BaseModel):                       # SAÍDA do login
    access_token: str
    token_type: str = "bearer"
```

| Schema | Direção | Função |
|--------|---------|--------|
| `UserCreate` | **Entrada** | Valida o e-mail e exige senha entre 8 e 72 caracteres |
| `UserRead` | **Saída** | Devolve só `id`, `email`, `is_active` — **omite o hash da senha** |
| `Token` | **Saída** | Empacota o JWT como `{access_token, token_type}` |

---

## Detalhes importantes

### 🔐 `UserRead` não expõe a senha
`UserRead` **não tem** o campo `hashed_password`. Como as rotas declaram `response_model=UserRead`, o FastAPI **filtra** a resposta automaticamente — mesmo que a função retorne o objeto `User` completo (com hash), o hash **jamais** chega ao cliente. É uma proteção de segurança que acontece "de graça".

### 🧩 `EmailStr`
Valida que o texto tem **formato** de e-mail (`algo@dominio.com`). Se vier inválido, o FastAPI responde `422 Unprocessable Entity` antes mesmo de a rota rodar. (Requer o pacote `email-validator`, que está no `requirements.txt`.)

### 📏 `Field(min_length=8, max_length=72)`
- **Mínimo 8**: política simples de senha forte.
- **Máximo 72**: o algoritmo **bcrypt trunca silenciosamente** senhas acima de 72 bytes. Limitar aqui evita comportamento confuso e um bug conhecido (documentado no `ARQUITETURA.md`).

### 🧩 `from_attributes=True` (antigo `orm_mode`)
Autoriza o Pydantic a construir um `UserRead` lendo os **atributos de um objeto** (`user.id`, `user.email`...), e não apenas de um dicionário. É o que permite retornar um objeto SQLAlchemy `User` direto da rota e o FastAPI convertê-lo para `UserRead`.

### 🧩 `Token.token_type = "bearer"`
Valor fixo. O padrão OAuth2/JWT espera que o cliente use o token no header como `Authorization: Bearer <token>`. Por isso o tipo é sempre `"bearer"`.

---

## Onde cada schema é usado

```
POST /auth/register   recebe UserCreate   →  responde UserRead
POST /auth/login      (form OAuth2)        →  responde Token
GET  /users/me        (header Bearer)      →  responde UserRead
```

🔗 Veja também: [api.md](api.md) (onde os schemas são declarados nas rotas), [models.md](models.md) (a diferença model vs schema).
