def test_register(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "joao@teste.com",
            "password": "senha123456",
        },
    )

    assert response.status_code == 201 #aqui verificamos se o status code é 201 (Created), indicando que o usuário foi criado com sucesso.
    data = response.json() #aqui extraímos os dados da resposta JSON para verificar se o usuário foi criado corretamente.

    assert data["email"] == "joao@teste.com"
    assert data["is_active"] is True
    assert "hashed_password" not in data


def test_register_email_duplicado(client):
    payload = {
        "email": "joao@teste.com",
        "password": "senha123456",
    }

    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "E-mail já cadastrado"


def test_login_e_users_me(client):
    payload = {
        "email": "joao@teste.com",
        "password": "senha123456",
    }

    client.post("/auth/register", json=payload)

    login_response = client.post(
        "/auth/login",
        data={
            "username": "joao@teste.com",
            "password": "senha123456",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "joao@teste.com"


def test_users_me_sem_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401