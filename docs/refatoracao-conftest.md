# Por que o `conftest.py` foi refatorado

> Contexto: ao adicionar testes negativos (veja [componentes/tests.md](componentes/tests.md)), em especial o teste de **usuário inativo → 403**, foi necessário mudar a estrutura de fixtures do `conftest.py`. Este documento explica o porquê.

A resposta curta: **o teste de usuário inativo precisa mexer no banco diretamente, e o `conftest` antigo não dava como fazer isso.**

---

## O problema

Veja o que o teste de usuário inativo precisa fazer:

```python
def test_users_me_usuario_inativo(client, db_session):
    client.post("/auth/register", json=USUARIO)      # cria via API (is_active=True)
    user = db_session.query(User)...                 # ← preciso de acesso ao banco aqui
    user.is_active = False                           # desativo o usuário
    db_session.commit()
    ...
```

Não existe um endpoint HTTP do tipo "desativar usuário". O `register` sempre cria com `is_active=True`. Então a **única** forma de testar o caminho do `403` ("usuário inativo") é **alterar o `is_active` direto no banco**. Para isso, o teste precisa de uma **sessão de banco** — e o `conftest` antigo não expunha nenhuma.

---

## Por que não bastava criar uma sessão separada

A tentação seria: "crio uma segunda sessão só para o teste". Mas aí cairia numa armadilha clássica:

- O **teste** escreveria `is_active=False` pela **sessão A**.
- A **API** (no `get_current_user`) leria o usuário por uma **sessão B diferente**.

Duas sessões = duas "conversas" distintas com o banco, cada uma com seu cache de objetos (*identity map*) e seu controle de transação. A alteração feita na sessão A poderia **não estar visível** na sessão B no momento da leitura — o teste ficaria frágil ou simplesmente não enxergaria a mudança.

---

## A solução: teste e API compartilham a MESMA sessão

A refatoração separou as responsabilidades em duas fixtures encadeadas:

```
db_session  →  cria as tabelas, abre UMA sessão, e no fim fecha + derruba as tabelas
    │
    ▼
client      →  depende de db_session e faz o override de get_db para
               devolver ESSA MESMA sessão aos endpoints
```

Antes (resumido), o `client` criava a própria sessão internamente e ninguém de fora a alcançava:

```python
# ANTES — sessão "presa" dentro do client
@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    def override_get_db():
        db = TestingSessionLocal()   # ← sessão criada aqui, invisível ao teste
        ...
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    ...
```

Depois, a sessão "sai para fora" via `db_session`, e o `client` reaproveita ela:

```python
# DEPOIS — a sessão é da fixture db_session, e o client usa a mesma
@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session             # ← MESMA sessão que o teste tem em mãos
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

Com isso, quando o teste faz `db_session.commit()` para desativar o usuário, a API — usando a **mesma** sessão — enxerga a mudança na hora, e o `get_current_user` corretamente devolve `403`.

---

## Benefícios extras da refatoração

- **Padrão consagrado:** essa dupla `db_session` + `client` é o jeito recomendado de testar FastAPI + SQLAlchemy. Vale para qualquer teste futuro que precise preparar dados (*seed*) ou inspecionar o banco.
- **Ciclo de vida mais limpo:** agora quem cuida de criar/derrubar tabelas e fechar a sessão é uma única fixture (`db_session`), em vez de espalhar isso no `client`.
- **Compatibilidade:** os testes antigos, que só usam `client`, continuam funcionando sem mudança (o `client` puxa o `db_session` automaticamente).

---

## Resultado

Após a refatoração, a suíte cobre o fluxo principal **e** os cenários de erro:

| Teste | Cenário | Espera |
|-------|---------|--------|
| `test_register` | cadastro com sucesso (sem vazar hash) | `201` |
| `test_register_email_duplicado` | e-mail repetido | `409` |
| `test_login_e_users_me` | registra → loga → acessa `/users/me` | `200` |
| `test_login_senha_errada` | senha incorreta | `401` |
| `test_login_email_inexistente` | e-mail não cadastrado | `401` |
| `test_users_me_sem_token` | rota protegida sem token | `401` |
| `test_users_me_token_invalido` | token malformado/assinatura inválida | `401` |
| `test_users_me_usuario_inativo` | token válido, mas usuário inativo | `403` |
| `test_register_senha_curta` | senha com menos de 8 caracteres | `422` |
| `test_register_email_invalido` | e-mail em formato inválido | `422` |

🔗 Veja também: [componentes/tests.md](componentes/tests.md) (como os testes funcionam), [componentes/core.md](componentes/core.md) (a dependência `get_db` que é substituída).
