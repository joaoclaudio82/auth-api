# Componente `models/` — Modelos ORM (SQLAlchemy)

> Pasta: [`app/models/`](../../app/models/)
> Arquivo: `user.py`

A camada `models/` faz o **mapeamento objeto-relacional (ORM)**: cada classe Python corresponde a uma tabela do banco. Em vez de escrever SQL na mão (`CREATE TABLE`, `INSERT`...), descrevemos a tabela como uma classe e o SQLAlchemy cuida do resto.

---

## `user.py` — A tabela `users`

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
```

A classe `User` herda de `Base` (definida em [core/database.py](core.md)) e usa a sintaxe moderna do **SQLAlchemy 2.0**: `Mapped[tipo]` + `mapped_column(...)`.

### As colunas, uma a uma

| Coluna | Tipo | Restrições | Observação |
|--------|------|-----------|-----------|
| `id` | Integer | PK, indexada | Gerado automaticamente pelo banco |
| `email` | String(255) | **único**, indexado, NOT NULL | A unicidade impede e-mails duplicados |
| `hashed_password` | String(255) | NOT NULL | Guarda **só o hash**, nunca a senha pura |
| `is_active` | Boolean | default `True`, NOT NULL | Permite "desativar" um usuário sem apagá-lo |
| `created_at` | DateTime(timezone) | `server_default=now()`, NOT NULL | O **banco** carimba a data de criação |

### Detalhes importantes

> 🧩 **`server_default=func.now()`** — a data de criação é definida pelo **PostgreSQL** no momento do INSERT, e não pelo Python. Isso é mais confiável e consistente entre processos diferentes.

> 🧩 **`unique=True` no `email`** — é a garantia *no nível do banco* de que não há e-mails duplicados. A verificação na rota de registro (que retorna `409`) é a primeira linha de defesa; o índice único é a rede de segurança final.

> 🔐 **`hashed_password`** — o próprio nome reforça a regra do projeto: nunca se guarda a senha em texto puro, apenas o hash bcrypt gerado em [security.py](core.md).

> 📑 **`index=True`** em `id` e `email` — cria índices no banco que aceleram as buscas. Como o login e o registro buscam usuários **por e-mail**, indexar essa coluna é importante para a performance.

---

## Como o model se conecta ao resto

```
models/user.py  ──herda──▶  core/database.py (Base)
       │
       │ é registrado em Base.metadata
       ▼
alembic/  lê Base.metadata para gerar/aplicar as migrations  (ver alembic.md)
       │
       ▼
services/user_service.py  cria e consulta objetos User  (ver services.md)
```

> ⚠️ **O model NÃO cria a tabela sozinho.** Definir a classe `User` apenas descreve a estrutura desejada. Quem efetivamente cria a tabela `users` no banco é o **Alembic**, aplicando a migration (`alembic upgrade head`). Veja [alembic.md](alembic.md).

🔗 Veja também: [schemas.md](schemas.md) (a diferença entre **model** e **schema**), [alembic.md](alembic.md).
