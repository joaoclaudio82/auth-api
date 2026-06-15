# Componente `alembic/` — Migrations (versionamento do banco)

> Pasta: [`alembic/`](../../alembic/) · arquivo de config: [`alembic.ini`](../../alembic.ini)
> Arquivos-chave: `alembic/env.py`, `alembic/versions/d37ec71b4f0c_create_users_table.py`

O **Alembic** é a ferramenta que **versiona o banco de dados**. Em vez de criar tabelas "na mão" no PostgreSQL, descrevemos cada mudança de estrutura em um arquivo de **migration**. Isso permite reproduzir exatamente a mesma estrutura em qualquer ambiente (dev, produção, CI) e voltar atrás quando necessário.

> 🧩 **Analogia:** o Alembic é como o "Git do banco de dados". Cada migration é um "commit" da estrutura, e `alembic upgrade head` aplica todos os commits até o mais recente.

---

## `alembic.ini` — Configuração

Arquivo de configuração padrão do Alembic. O ponto relevante:
- `script_location = alembic` → onde ficam as migrations.
- `sqlalchemy.url = driver://user:pass@localhost/dbname` → é apenas um **placeholder**. A URL real é injetada pelo `env.py` (veja abaixo), usando a mesma `DATABASE_URL` da aplicação.

---

## `env.py` — A ponte Alembic ↔ aplicação

```python
from app.core.config import settings
from app.core.database import Base
from app.models.user import User          # importa o model para registrá-lo

config.set_main_option("sqlalchemy.url", settings.database_url)  # mesma URL do app
target_metadata = Base.metadata                                  # Alembic "enxerga" os models
```

Três ajustes tornam o `--autogenerate` possível:

1. **`config.set_main_option("sqlalchemy.url", settings.database_url)`** — força o Alembic a usar **a mesma** `DATABASE_URL` da aplicação, em vez do placeholder do `alembic.ini`.
2. **`target_metadata = Base.metadata`** — entrega ao Alembic o catálogo de todas as tabelas declaradas via `Base`. Comparando esse catálogo com o banco real, ele consegue gerar migrations sozinho.
3. **`from app.models.user import User`** — esse import é **necessário** para que a classe `User` seja **carregada** e, assim, registrada em `Base.metadata`. Sem o import, o Alembic não enxergaria a tabela `users`.

> 💡 **Regra prática:** sempre que você criar um **novo model**, lembre-se de importá-lo em `env.py` — senão o `--autogenerate` não vai detectá-lo.

---

## `versions/d37ec71b4f0c_create_users_table.py` — A migration

```python
revision = 'd37ec71b4f0c'
down_revision = None          # ← é a PRIMEIRA migration (não há anterior)

def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
```

- **`upgrade()`** — o que fazer para **avançar** (criar a tabela `users` e seus índices). É o que roda no `alembic upgrade head`.
- **`downgrade()`** — como **reverter** (derrubar índices e tabela). Permite voltar atrás com segurança via `alembic downgrade -1`.
- **`revision` / `down_revision`** — formam a "corrente" de migrations. Como `down_revision = None`, esta é a **primeira** da cadeia.

> 🔎 Note que a estrutura criada aqui **espelha exatamente** o model `User` ([models.md](models.md)). Foi gerada automaticamente comparando `Base.metadata` com o banco vazio.

---

## Comandos do dia a dia

```bash
# Gerar uma nova migration automaticamente (depois de alterar/criar um model)
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar todas as migrations pendentes (avançar até a última)
alembic upgrade head

# Reverter a última migration
alembic downgrade -1

# Ver em qual versão o banco está
alembic current
```

> 🐳 **No Docker:** o `docker-compose.yml` roda `alembic upgrade head` automaticamente no start da API, antes de subir o uvicorn. Ou seja, ao subir os containers o banco já é migrado sozinho (veja [../docker-compose.md](../docker-compose.md)).

---

## O que fica no banco depois

Após `alembic upgrade head`, o PostgreSQL terá duas tabelas:
- **`users`** — a tabela da aplicação.
- **`alembic_version`** — controlada pelo Alembic, guarda qual migration já foi aplicada (para ele saber o que falta rodar).

🔗 Veja também: [models.md](models.md) (a fonte da estrutura), [core.md](core.md) (`Base` e `settings`).
