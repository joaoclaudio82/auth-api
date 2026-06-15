# Componente `services/` — Regra de negócio

> Pasta: [`app/services/`](../../app/services/)
> Arquivo: `user_service.py`

A camada `services/` é onde mora a **inteligência da aplicação**: as regras de negócio. Ela usa os **models** (para falar com o banco) e a **segurança** (para hash de senha), mas **não conhece HTTP** — não importa `HTTPException`, não decide status codes.

> 🏛️ **Regra de ouro:** o serviço diz apenas "deu certo" ou "não deu" / "autenticou" ou "não autenticou". **Quem traduz isso em uma resposta HTTP é a camada de rotas** ([api.md](api.md)). Isso mantém o serviço reutilizável fora da web (ex.: num script, num job, em testes).

---

## `user_service.py` — Três funções

### 1. `get_by_email` — consulta por e-mail

```python
def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()
```

Busca um usuário pelo e-mail. Retorna o `User` ou `None`. É reutilizada **no cadastro** (para checar duplicata) e **no login/rota protegida** (para encontrar o usuário).

### 2. `create_user` — cadastra um usuário

```python
def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),  # ← hash aqui!
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)        # recarrega para pegar o id gerado pelo banco
        return user
    except IntegrityError:
        db.rollback()
        raise ValueError("E-mail já cadastrado")
```

Encapsula o fluxo `hash → add → commit → refresh`:
- A senha vira **hash** antes de tocar o banco.
- `db.add` coloca o objeto na sessão; `db.commit` confirma o `INSERT`; `db.refresh` recarrega o objeto para obter o `id` gerado pelo banco.

> 🛡️ **Tratamento transacional de erro:** se o `commit` falhar por violação de unicidade (`IntegrityError` — e-mail duplicado em uma corrida entre requisições), a função faz `db.rollback()` e levanta um `ValueError`. Isso protege contra o caso em que dois cadastros do mesmo e-mail passam pela verificação `get_by_email` quase ao mesmo tempo. O `rollback` evita deixar a sessão em estado inconsistente.

### 3. `authenticate` — valida credenciais (login)

```python
def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if not user:
        return None                                  # email não existe
    if not verify_password(password, user.hashed_password):
        return None                                  # senha errada
    return user                                      # ok!
```

Busca o usuário e compara a senha digitada com o hash salvo via `verify_password`. Devolve o `User` (sucesso) ou `None` (e-mail inexistente **ou** senha errada).

> 🔐 **Por que `None` nos dois casos de falha?** Retornar a mesma resposta para "e-mail não existe" e "senha errada" evita revelar a um atacante se um e-mail está ou não cadastrado. A rota transforma esse `None` em um `401` genérico ("Credenciais inválidas").

---

## A decisão arquitetural central (documentada no próprio código)

O serviço **retorna `None`** (ou levanta um erro de domínio como `ValueError`) em vez de lançar `HTTPException`. Por quê?

- `HTTPException` pertence ao **mundo HTTP**, que é responsabilidade da camada de **API**.
- O serviço fica **independente do protocolo** — poderia ser chamado por um worker, um CLI, etc.
- A tradução "resultado de negócio → status HTTP" fica **num único lugar** (a rota).

---

## Resumo

| Função | Entrada | Saída | Usada por |
|--------|---------|-------|-----------|
| `get_by_email` | `db`, `email` | `User \| None` | register, login, rota protegida |
| `create_user` | `db`, `UserCreate` | `User` (ou `ValueError`) | `POST /auth/register` |
| `authenticate` | `db`, `email`, `password` | `User \| None` | `POST /auth/login` |

🔗 Veja também: [api.md](api.md) (quem chama o serviço), [core.md](core.md) (`security` e `get_db`), [models.md](models.md) (`User`).
