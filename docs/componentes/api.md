# Componente `api/` — Rotas HTTP (FastAPI)

> Pasta: [`app/api/`](../../app/api/)
> Arquivos: `auth.py`, `users.py`
> (relacionado: `app/main.py`, que junta tudo)

A camada `api/` é a **porta de entrada HTTP** da aplicação. Ela recebe as requisições, valida a entrada com schemas, decide o status HTTP de resposta e **delega a regra de negócio para os services**. Ela **não faz SQL**, **não faz hash** e **não monta JWT na mão** — só orquestra.

---

## `app/main.py` — O ponto de entrada

```python
from fastapi import FastAPI
from app.api import auth, users

app = FastAPI(title="auth-api-fast", version="1.0.0")

app.include_router(auth.router)    # adiciona /auth/register e /auth/login
app.include_router(users.router)   # adiciona /users/me

@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}
```

É o *composition root* — onde as peças se juntam. Ele cria a instância `app`, **registra os routers** e define o `/health` (usado para checar se o serviço está no ar).

> 🧩 **Router** — o FastAPI permite quebrar as rotas em "mini-aplicações" (`APIRouter`). Cada arquivo em `api/` define um router com seu próprio prefixo (`/auth`, `/users`), e o `main.py` só os "pluga". Isso evita um `main.py` gigante.

---

## `auth.py` — Cadastro e login

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
- ✅ Valida a entrada (`UserCreate` no register; `OAuth2PasswordRequestForm` no login).
- ✅ Decide os códigos HTTP: `201 Created`, `409 Conflict`, `401 Unauthorized`.
- ✅ Delega a lógica ao `user_service`.
- ❌ **Não** faz SQL, hash ou JWT diretamente.

> 🧩 **`OAuth2PasswordRequestForm`** é um formulário padrão do OAuth2. Espera os campos `username` e `password` enviados como **form-urlencoded** (não JSON!). Aqui, o `username` carrega o **e-mail**. Usar esse formato padrão é o que faz o botão **Authorize** do Swagger funcionar automaticamente.

> 🔁 **Injeção de dependência** `db: Session = Depends(get_db)`: cada requisição recebe uma sessão de banco nova e isolada (veja [core.md](core.md)).

---

## `users.py` — A rota protegida e o "guardião"

```python
router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> User:
    email = decode_token(token)
    if email is None:
        raise HTTPException(401, "Token inválido ou expirado")
    user = user_service.get_by_email(db, email)
    if user is None:
        raise HTTPException(401, "Usuário não encontrado")
    if not user.is_active:
        raise HTTPException(403, "Usuário inativo")
    return user

@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
```

Aqui aparece um dos padrões mais elegantes do FastAPI: a **dependência como guardião de rota**.

- **`oauth2_scheme`** sabe **extrair** o token do header `Authorization: Bearer <token>`. Ele só pega a string — **não valida** o JWT.
- **`get_current_user`** é quem de fato **valida**: decodifica o token, extrai o e-mail (`sub`), busca o usuário e confere se está ativo. Qualquer falha vira `401` (token/usuário) ou `403` (usuário inativo).
- **`read_me`** apenas declara `Depends(get_current_user)`. Se o token for inválido, o FastAPI **nem entra** na função — corta antes. Se for válido, `current_user` já chega pronto.

> 🧩 **Por que isso é poderoso?** Qualquer rota nova que precise de autenticação só adiciona `current_user: User = Depends(get_current_user)`. A lógica de validação fica num único lugar (princípio DRY).

> 🔎 **`tokenUrl="/auth/login"`** informa ao Swagger onde obter o token quando você clica em **Authorize**. É integração/documentação — não muda a lógica de validação.

---

## As rotas em uma tabela

| Método | Caminho | Entrada | Saída | Códigos |
|--------|---------|---------|-------|---------|
| `POST` | `/auth/register` | `UserCreate` (JSON) | `UserRead` | `201`, `409` |
| `POST` | `/auth/login` | form `username`+`password` | `Token` | `200`, `401` |
| `GET` | `/users/me` | header `Bearer <token>` | `UserRead` | `200`, `401`, `403` |
| `GET` | `/health` | — | `{"status":"ok"}` | `200` |

🔗 Veja também: [services.md](services.md) (a quem as rotas delegam), [schemas.md](schemas.md) (os contratos), [core.md](core.md) (`get_db`, `security`).
