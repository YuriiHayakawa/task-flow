"""T096/T099 [US10] — anexos em tarefas via HTTP: upload com validação de
tipo/tamanho, listagem, download, remoção por uploader ou Owner/Admin,
prevenção de path traversal.

Cobre: FR-037, FR-038, contracts/collaboration.md (`GET/POST
/tasks/{task_id}/attachments`, `GET .../attachments/{id}/download`,
`DELETE .../attachments/{id}`).

Isolado do disco real via `tmp_path` (fixture `_isolated_attachments_dir`,
autouse) — nenhum teste desta suíte grava fora de um diretório descartável
do pytest."""

import uuid

import pytest

from app.core.config import settings
from app.enums.workspace_role import WorkspaceRole
from app.models.attachment import Attachment


@pytest.fixture(autouse=True)
def _isolated_attachments_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ATTACHMENTS_DIR", str(tmp_path))
    return tmp_path


def _upload(client, task_id, user, auth_headers, *, filename="documento.pdf", content=b"conteudo",
            content_type="application/pdf"):
    return client.post(
        f"/api/v1/tasks/{task_id}/attachments",
        files={"file": (filename, content, content_type)},
        headers=auth_headers(user),
    )


# --- POST /tasks/{task_id}/attachments ------------------------------------------


def test_upload_by_assignee_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    assignee = make_user(email="assignee-upload@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    response = _upload(client, task.id, assignee, auth_headers, filename="relatorio.pdf")

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "relatorio.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(b"conteudo")
    assert body["uploaded_by_id"] == str(assignee.id)
    assert body["uploaded_by_name"] == assignee.name
    assert body["uploaded_by_email"] == assignee.email
    assert body["created_at"] is not None


def test_upload_writes_physical_file(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    _upload(client, task.id, owner, auth_headers, content=b"dados do arquivo")

    written_files = list(tmp_path.iterdir())
    assert len(written_files) == 1
    assert written_files[0].read_bytes() == b"dados do arquivo"


def test_upload_explicit_participant_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    from app.models.task_member import TaskMember

    owner = make_user()
    participant = make_user(email="participant-upload@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = _upload(client, task.id, participant, auth_headers)

    assert response.status_code == 201


def test_upload_personal_task_creator_success(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = _upload(client, task.id, creator, auth_headers)

    assert response.status_code == 201


def test_upload_plain_member_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    plain_member = make_user(email="plain-member-upload@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = _upload(client, task.id, plain_member, auth_headers)

    assert response.status_code == 403


def test_upload_owner_admin_not_participant_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-upload@example.com")
    creator = make_user(email="creator-upload@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response_owner = _upload(client, task.id, owner, auth_headers)
    response_admin = _upload(client, task.id, admin, auth_headers)

    assert response_owner.status_code == 403
    assert response_admin.status_code == 403


def test_upload_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-upload@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = _upload(client, task.id, outsider, auth_headers)

    assert response.status_code == 404


def test_upload_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = _upload(client, uuid.uuid4(), user, auth_headers)

    assert response.status_code == 404


def test_upload_rejects_disallowed_content_type(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = _upload(
        client, task.id, owner, auth_headers, filename="virus.exe", content_type="application/x-msdownload"
    )

    assert response.status_code == 400


def test_upload_rejects_oversized_file(client, make_user, make_workspace, make_task, auth_headers, tmp_path):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    oversized_content = b"x" * (settings.ATTACHMENTS_MAX_SIZE_BYTES + 1)

    response = _upload(client, task.id, owner, auth_headers, content=oversized_content)

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_prevents_path_traversal_in_storage_filename(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    """research.md #12: mesmo com um nome original malicioso, o arquivo
    nunca é gravado fora de `ATTACHMENTS_DIR` — o nome de armazenamento é
    sempre um UUID, e `original_filename` (exibição apenas) preserva o valor
    enviado, sem afetar o caminho físico."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = _upload(
        client, task.id, owner, auth_headers, filename="../../../etc/passwd", content_type="text/plain"
    )

    assert response.status_code == 201
    assert response.json()["original_filename"] == "../../../etc/passwd"
    written_files = list(tmp_path.iterdir())
    assert len(written_files) == 1
    assert written_files[0].parent == tmp_path  # nenhum diretório extra criado


# --- GET /tasks/{task_id}/attachments --------------------------------------------


def test_list_attachments_empty(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/attachments", headers=auth_headers(owner))

    assert response.status_code == 200
    assert response.json() == []


def test_list_attachments_multiple(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(
        Attachment(
            task_id=task.id,
            uploaded_by_id=owner.id,
            original_filename="a.pdf",
            storage_path=f"{uuid.uuid4()}.pdf",
            content_type="application/pdf",
            size_bytes=10,
        )
    )
    db_session.add(
        Attachment(
            task_id=task.id,
            uploaded_by_id=owner.id,
            original_filename="b.pdf",
            storage_path=f"{uuid.uuid4()}.pdf",
            content_type="application/pdf",
            size_bytes=20,
        )
    )
    db_session.flush()

    response = client.get(f"/api/v1/tasks/{task.id}/attachments", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["original_filename"] for item in body} == {"a.pdf", "b.pdf"}


def test_list_attachments_any_workspace_member_can_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="member-list-attachments@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/attachments", headers=auth_headers(member))

    assert response.status_code == 200


def test_list_attachments_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-list-attachments@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/attachments", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_list_attachments_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}/attachments", headers=auth_headers(user))

    assert response.status_code == 404


# --- GET /tasks/{task_id}/attachments/{attachment_id}/download ------------------


def test_download_returns_file_content(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    upload_response = _upload(client, task.id, owner, auth_headers, filename="baixar.pdf", content=b"conteudo para baixar")
    attachment_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}/download", headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.content == b"conteudo para baixar"
    assert "baixar.pdf" in response.headers.get("content-disposition", "")


def test_download_visible_to_workspace_member_without_participation(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    """FR-037/Acceptance Scenario 3: um membro do workspace que não é
    participante MUST continuar conseguindo visualizar/baixar anexos já
    existentes, mesmo sem poder enviar novos."""
    owner = make_user()
    plain_member = make_user(email="plain-member-download@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    upload_response = _upload(client, task.id, owner, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}/download",
        headers=auth_headers(plain_member),
    )

    assert response.status_code == 200


def test_download_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-download@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    upload_response = _upload(client, task.id, owner, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}/download", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_download_nonexistent_attachment_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(
        f"/api/v1/tasks/{task.id}/attachments/{uuid.uuid4()}/download", headers=auth_headers(owner)
    )

    assert response.status_code == 404


# --- DELETE /tasks/{task_id}/attachments/{attachment_id} ------------------------


def test_delete_by_uploader_success(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    upload_response = _upload(client, task.id, owner, auth_headers)
    attachment_id = upload_response.json()["id"]
    assert len(list(tmp_path.iterdir())) == 1

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204
    assert response.content == b""
    assert list(tmp_path.iterdir()) == []
    list_response = client.get(f"/api/v1/tasks/{task.id}/attachments", headers=auth_headers(owner))
    assert list_response.json() == []


def test_delete_by_workspace_admin_not_uploader_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-delete-attachment@example.com")
    uploader = make_user(email="uploader-delete-attachment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=uploader, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=uploader, workspace=workspace)
    upload_response = _upload(client, task.id, uploader, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_headers(admin)
    )

    assert response.status_code == 204


def test_delete_by_workspace_owner_not_uploader_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    uploader = make_user(email="uploader-delete-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=uploader, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=uploader, workspace=workspace)
    upload_response = _upload(client, task.id, uploader, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204


def test_delete_by_plain_member_not_uploader_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    plain_member = make_user(email="plain-member-delete-attachment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    upload_response = _upload(client, task.id, owner, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_headers(plain_member)
    )

    assert response.status_code == 403


def test_delete_personal_task_by_someone_else_forbidden(
    client, make_user, make_task, auth_headers
):
    """Tarefa pessoal não tem workspace — sem Owner/Admin para atuar como
    via administrativa; só o uploader remove."""
    creator = make_user()
    someone_else = make_user(email="someone-else-delete-personal@example.com")
    task = make_task(creator=creator)
    upload_response = _upload(client, task.id, creator, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_headers(someone_else)
    )

    assert response.status_code == 404  # someone_else nem enxerga a tarefa pessoal


def test_delete_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-delete-attachment@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    upload_response = _upload(client, task.id, owner, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_delete_nonexistent_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.delete(
        f"/api/v1/tasks/{task.id}/attachments/{uuid.uuid4()}", headers=auth_headers(owner)
    )

    assert response.status_code == 404


def test_delete_from_another_task_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    upload_response = _upload(client, task_1.id, owner, auth_headers)
    attachment_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/tasks/{task_2.id}/attachments/{attachment_id}", headers=auth_headers(owner)
    )

    assert response.status_code == 404


# --- Isolamento entre workspaces -------------------------------------------------


def test_isolation_member_of_other_workspace_cannot_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    member_b = make_user(email="member-b-attachments-isolation@example.com")
    add_workspace_member(workspace=workspace_b, user=member_b, role=WorkspaceRole.MEMBER)
    task_in_a = make_task(creator=owner, workspace=workspace_a)

    response = client.get(
        f"/api/v1/tasks/{task_in_a.id}/attachments", headers=auth_headers(member_b)
    )

    assert response.status_code == 404


# --- Regressão -----------------------------------------------------------------


def test_checklist_endpoint_still_works(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(owner))

    assert response.status_code == 200


def test_comments_endpoint_still_works(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(owner))

    assert response.status_code == 200
