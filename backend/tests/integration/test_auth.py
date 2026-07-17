"""T037 [US1] — cadastro, login, rotas protegidas e conta desativada.

Cobre: FR-001 a FR-004, research.md #1 (ACCOUNT_DISABLED distinto de
INVALID_CREDENTIALS, revalidação de is_active a cada requisição)."""


def test_register_creates_user_and_never_exposes_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Ana Silva", "email": "Ana@Example.com", "password": "supersecret123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ana Silva"
    assert body["email"] == "ana@example.com"  # normalizado para lowercase (research.md #10)
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email_case_insensitive(client, make_user):
    make_user(email="duplicado@example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Outro", "email": "DUPLICADO@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Ana", "email": "ana2@example.com", "password": "curta"},
    )

    assert response.status_code == 422


def test_login_succeeds_with_correct_credentials(client, make_user):
    make_user(email="login@example.com", password="supersecret123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_rejects_wrong_password_with_invalid_credentials(client, make_user):
    make_user(email="wrongpass@example.com", password="supersecret123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_unknown_email_with_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ninguem@example.com", "password": "whatever123"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_disabled_account_returns_account_disabled_not_generic(client, make_user):
    make_user(email="disabled@example.com", password="supersecret123", is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "disabled@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "ACCOUNT_DISABLED"
    assert body["error"]["code"] != "INVALID_CREDENTIALS"


def test_protected_route_requires_authentication(client):
    response = client.get("/api/v1/tasks")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_protected_route_rejects_token_of_deactivated_account(
    client, make_user, auth_headers, db_session
):
    """research.md #1: is_active é revalidado a cada requisição — desativar a
    conta depois de emitido o token deve derrubar o acesso imediatamente."""
    user = make_user(email="revoked@example.com", is_active=True)
    headers = auth_headers(user)

    user.is_active = False
    db_session.flush()

    response = client.get("/api/v1/tasks", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"
