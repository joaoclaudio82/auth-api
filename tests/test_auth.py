from app.models.user import User

# Dados reutilizados em vários testes.
USUARIO = {
    "email": "joao@teste.com",
    "password": "senha123456",
}


# ===================== FLUXO PRINCIPAL (caminho feliz) =====================

def test_register(client):
    response = client.post("/auth/register", json=USUARIO)

    assert response.status_code == 201  # 201 (Created): usuário criado com sucesso
    data = response.json()

    assert data["email"] == USUARIO["email"]
    assert data["is_active"] is True
    assert "hashed_password" not in data  # o hash da senha nunca pode vazar na resposta


def test_register_email_duplicado(client):
    client.post("/auth/register", json=USUARIO)
    response = client.post("/auth/register", json=USUARIO)

    assert response.status_code == 409
    assert response.json()["detail"] == "E-mail já cadastrado"


def test_login_e_users_me(client):
    client.post("/auth/register", json=USUARIO)

    login_response = client.post(
        "/auth/login",
        data={"username": USUARIO["email"], "password": USUARIO["password"]},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == USUARIO["email"]


# ===================== TESTES NEGATIVOS (cenários de erro) =====================

def test_login_senha_errada(client):
    """Senha incorreta deve resultar em 401 Unauthorized."""
    client.post("/auth/register", json=USUARIO)

    response = client.post(
        "/auth/login",
        data={"username": USUARIO["email"], "password": "senha-errada-123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"


def test_login_email_inexistente(client):
    """E-mail que não existe deve resultar em 401 (mesma resposta de senha errada)."""
    response = client.post(
        "/auth/login",
        data={"username": "naoexiste@teste.com", "password": USUARIO["password"]},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"


def test_users_me_sem_token(client):
    """Acessar rota protegida sem token deve resultar em 401."""
    response = client.get("/users/me")

    assert response.status_code == 401


def test_users_me_token_invalido(client):
    """Token malformado/assinatura inválida deve resultar em 401."""
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer este-token-nao-e-valido"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado"


def test_users_me_usuario_inativo(client, db_session):
    """Usuário inativo, mesmo com token válido, deve receber 403 Forbidden."""
    client.post("/auth/register", json=USUARIO)

    # desativa o usuário diretamente no banco (mesma sessão usada pela API)
    user = db_session.query(User).filter(User.email == USUARIO["email"]).first()
    user.is_active = False
    db_session.commit()

    # o login ainda funciona (authenticate só checa e-mail + senha)
    login = client.post(
        "/auth/login",
        data={"username": USUARIO["email"], "password": USUARIO["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    # mas a rota protegida bloqueia por usuário inativo
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Usuário inativo"


def test_register_senha_curta(client):
    """Senha com menos de 8 caracteres deve falhar na validação (422)."""
    response = client.post(
        "/auth/register",
        json={"email": USUARIO["email"], "password": "curta"},
    )

    assert response.status_code == 422


def test_register_email_invalido(client):
    """E-mail em formato inválido deve falhar na validação (422)."""
    response = client.post(
        "/auth/register",
        json={"email": "isto-nao-e-email", "password": USUARIO["password"]},
    )

    assert response.status_code == 422
