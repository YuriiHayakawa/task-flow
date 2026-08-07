"""T085 [US7] — perfil do usuário via HTTP: visualizar, editar nome/e-mail,
unicidade case-insensitive, campos fora do MVP rejeitados.

Cobre: FR-051 a FR-054, contracts/auth-and-users.md
(`GET/PATCH /users/me`)."""


# --- GET /users/lookup (Fase 20 — suporte a "adicionar membro por e-mail") -------


def test_lookup_by_email_returns_minimal_user_data(client, make_user, auth_headers):
    caller = make_user()
    target = make_user(name="Fulano de Tal", email="fulano-lookup@example.com")

    response = client.get(
        "/api/v1/users/lookup",
        params={"email": "fulano-lookup@example.com"},
        headers=auth_headers(caller),
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"id": str(target.id), "name": "Fulano de Tal", "email": "fulano-lookup@example.com"}
    assert "is_active" not in body
    assert "is_system_admin" not in body


def test_lookup_by_email_case_insensitive(client, make_user, auth_headers):
    caller = make_user()
    target = make_user(email="case-lookup@example.com")

    response = client.get(
        "/api/v1/users/lookup",
        params={"email": "CASE-LOOKUP@EXAMPLE.COM"},
        headers=auth_headers(caller),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(target.id)


def test_lookup_by_email_not_found_returns_404(client, make_user, auth_headers):
    caller = make_user()

    response = client.get(
        "/api/v1/users/lookup",
        params={"email": "ninguem-aqui@example.com"},
        headers=auth_headers(caller),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_lookup_by_email_requires_authentication(client):
    response = client.get("/api/v1/users/lookup", params={"email": "qualquer@example.com"})

    assert response.status_code == 401


# --- GET /users/me -------------------------------------------------------------


def test_get_me_returns_profile(client, make_user, auth_headers):
    user = make_user(name="Fulano", email="fulano@example.com")

    response = client.get("/api/v1/users/me", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["name"] == "Fulano"
    assert body["email"] == "fulano@example.com"
    assert body["is_active"] is True
    assert "created_at" in body


def test_get_me_requires_authentication(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_get_me_never_exposes_password_hash(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/users/me", headers=auth_headers(user))

    assert "password_hash" not in response.json()
    assert "password" not in response.json()


def test_get_me_disabled_account_returns_403(client, make_user, auth_headers):
    user = make_user(is_active=False)

    response = client.get("/api/v1/users/me", headers=auth_headers(user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


# --- PATCH /users/me: nome ------------------------------------------------------


def test_update_me_name_only(client, make_user, auth_headers):
    user = make_user(name="Nome Antigo", email="nome-antigo@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"name": "Nome Novo"}, headers=auth_headers(user)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Nome Novo"
    assert body["email"] == "nome-antigo@example.com"  # inalterado


def test_update_me_name_reflected_on_subsequent_get(client, make_user, auth_headers):
    user = make_user(name="Antes")
    headers = auth_headers(user)
    client.patch("/api/v1/users/me", json={"name": "Depois"}, headers=headers)

    response = client.get("/api/v1/users/me", headers=headers)

    assert response.json()["name"] == "Depois"


# --- PATCH /users/me: e-mail -----------------------------------------------------


def test_update_me_email_only(client, make_user, auth_headers):
    user = make_user(email="antigo@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"email": "novo@example.com"}, headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["email"] == "novo@example.com"


def test_update_me_email_normalized_to_lowercase(client, make_user, auth_headers):
    user = make_user(email="antigo2@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"email": "Novo.Email@Example.COM"}, headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["email"] == "novo.email@example.com"


def test_update_me_email_duplicate_rejected(client, make_user, auth_headers):
    make_user(email="ocupado@example.com")
    user = make_user(email="livre@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"email": "ocupado@example.com"}, headers=auth_headers(user)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_update_me_email_duplicate_case_insensitive_rejected(client, make_user, auth_headers):
    make_user(email="ocupado2@example.com")
    user = make_user(email="livre2@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"email": "OCUPADO2@EXAMPLE.COM"}, headers=auth_headers(user)
    )

    assert response.status_code == 409


def test_update_me_resend_own_email_unchanged_succeeds(client, make_user, auth_headers):
    """Reenviar o próprio e-mail (sem alterá-lo) não deve ser tratado como
    duplicidade — `email_taken` exclui o próprio usuário."""
    user = make_user(name="Nome", email="proprio@example.com")

    response = client.patch(
        "/api/v1/users/me",
        json={"name": "Nome Atualizado", "email": "proprio@example.com"},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "proprio@example.com"


def test_update_me_email_invalid_shape_returns_422(client, make_user, auth_headers):
    user = make_user()

    response = client.patch(
        "/api/v1/users/me", json={"email": "sem-arroba"}, headers=auth_headers(user)
    )

    assert response.status_code == 422


# --- PATCH /users/me: name + email juntos ---------------------------------------


def test_update_me_name_and_email_together(client, make_user, auth_headers):
    user = make_user(name="Antigo", email="antigo3@example.com")

    response = client.patch(
        "/api/v1/users/me",
        json={"name": "Novo Nome", "email": "novo3@example.com"},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Novo Nome"
    assert body["email"] == "novo3@example.com"


# --- PATCH /users/me: validação de corpo -----------------------------------------


def test_update_me_empty_body_returns_422(client, make_user, auth_headers):
    user = make_user()

    response = client.patch("/api/v1/users/me", json={}, headers=auth_headers(user))

    assert response.status_code == 422


def test_update_me_password_field_rejected(client, make_user, auth_headers):
    user = make_user()

    response = client.patch(
        "/api/v1/users/me",
        json={"name": "X", "password": "novasenha123"},
        headers=auth_headers(user),
    )

    assert response.status_code == 422


def test_update_me_photo_field_rejected(client, make_user, auth_headers):
    user = make_user()

    response = client.patch(
        "/api/v1/users/me", json={"name": "X", "photo": "base64..."}, headers=auth_headers(user)
    )

    assert response.status_code == 422


def test_update_me_requires_authentication(client):
    response = client.patch("/api/v1/users/me", json={"name": "X"})

    assert response.status_code == 401


def test_update_me_empty_name_returns_422(client, make_user, auth_headers):
    user = make_user()

    response = client.patch("/api/v1/users/me", json={"name": ""}, headers=auth_headers(user))

    assert response.status_code == 422


# --- Isolamento entre usuários ----------------------------------------------------


def test_update_me_only_affects_own_account(client, make_user, auth_headers):
    user = make_user(name="Usuário A", email="usuario-a@example.com")
    other = make_user(name="Usuário B", email="usuario-b@example.com")

    client.patch("/api/v1/users/me", json={"name": "A Renomeado"}, headers=auth_headers(user))

    response_other = client.get("/api/v1/users/me", headers=auth_headers(other))
    assert response_other.json()["name"] == "Usuário B"


# --- Regressão -----------------------------------------------------------------


def test_admin_routes_now_exist_in_openapi(client, make_user, auth_headers):
    """Fase 9 (T088): este teste originalmente confirmava que `/admin`
    ainda NÃO existia (regra de não antecipar a Fase 15). Agora que a
    Fase 15/US13 implementou o módulo, a premissa mudou — reescrito para
    confirmar o oposto: o endpoint existe e responde."""
    admin = make_user(email="admin-openapi-regression@example.com", is_system_admin=True)

    response = client.get("/api/v1/admin/users", headers=auth_headers(admin))

    assert response.status_code == 200


def test_task_members_endpoint_still_works(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200
