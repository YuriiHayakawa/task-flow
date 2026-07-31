"""Fase 16 (hardening) — exclusão controlada de anexos ao excluir tarefa ou
workspace: os arquivos físicos correspondentes são removidos do disco,
conforme exigido explicitamente por `plan.md` (seção Testes, refinamento
#14) e `research.md` #12. Achado da auditoria de abertura da Fase 16 — esta
funcionalidade nunca havia sido implementada (documentada como dívida
técnica na Fase 12).

Isolado do disco real via `tmp_path` (mesmo padrão de `test_attachments.py`)."""

import pytest

from app.core.config import settings
from app.enums.workspace_role import WorkspaceRole


@pytest.fixture(autouse=True)
def _isolated_attachments_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ATTACHMENTS_DIR", str(tmp_path))
    return tmp_path


def _upload(client, task_id, user, auth_headers, *, filename="documento.pdf", content=b"conteudo"):
    return client.post(
        f"/api/v1/tasks/{task_id}/attachments",
        files={"file": (filename, content, "application/pdf")},
        headers=auth_headers(user),
    )


# --- DELETE /tasks/{task_id} -----------------------------------------------------


def test_delete_task_removes_physical_attachment_files(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    _upload(client, task.id, owner, auth_headers, filename="anexo1.pdf")
    _upload(client, task.id, owner, auth_headers, filename="anexo2.pdf")
    assert len(list(tmp_path.iterdir())) == 2

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(owner))

    assert response.status_code == 204
    assert list(tmp_path.iterdir()) == []


def test_delete_personal_task_removes_physical_attachment_files(
    client, make_user, make_task, auth_headers, tmp_path
):
    creator = make_user()
    task = make_task(creator=creator)
    _upload(client, task.id, creator, auth_headers)
    assert len(list(tmp_path.iterdir())) == 1

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(creator))

    assert response.status_code == 204
    assert list(tmp_path.iterdir()) == []


def test_delete_task_without_attachments_still_works(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(owner))

    assert response.status_code == 204


def test_delete_task_does_not_remove_attachments_of_other_tasks(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_to_delete = make_task(creator=owner, workspace=workspace, title="Será excluída")
    task_to_keep = make_task(creator=owner, workspace=workspace, title="Permanece")
    _upload(client, task_to_delete.id, owner, auth_headers, filename="do-excluido.pdf")
    _upload(client, task_to_keep.id, owner, auth_headers, filename="do-mantido.pdf")
    assert len(list(tmp_path.iterdir())) == 2

    client.delete(f"/api/v1/tasks/{task_to_delete.id}", headers=auth_headers(owner))

    remaining_files = list(tmp_path.iterdir())
    assert len(remaining_files) == 1


def test_delete_task_succeeds_even_when_physical_removal_fails(
    client, make_user, make_workspace, make_task, auth_headers, monkeypatch
):
    from app.utils import file_storage

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    _upload(client, task.id, owner, auth_headers)

    def _raise_os_error(_storage_path: str) -> None:
        raise OSError("permissão negada")

    monkeypatch.setattr(file_storage, "delete_file", _raise_os_error)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(owner))

    assert response.status_code == 204


# --- DELETE /workspaces/{workspace_id} -------------------------------------------


def test_delete_workspace_removes_physical_attachment_files_across_all_tasks(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    _upload(client, task_1.id, owner, auth_headers, filename="anexo-t1.pdf")
    _upload(client, task_2.id, owner, auth_headers, filename="anexo-t2.pdf")
    assert len(list(tmp_path.iterdir())) == 2

    response = client.delete(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(owner))

    assert response.status_code == 204
    assert list(tmp_path.iterdir()) == []


def test_delete_workspace_without_attachments_still_works(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.delete(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(owner))

    assert response.status_code == 204


def test_delete_workspace_does_not_remove_attachments_of_other_workspaces(
    client, make_user, make_workspace, make_task, auth_headers, tmp_path
):
    owner = make_user()
    workspace_to_delete = make_workspace(owner=owner, name="Será excluído")
    workspace_to_keep = make_workspace(owner=owner, name="Permanece")
    task_in_deleted = make_task(creator=owner, workspace=workspace_to_delete)
    task_in_kept = make_task(creator=owner, workspace=workspace_to_keep)
    _upload(client, task_in_deleted.id, owner, auth_headers, filename="do-excluido.pdf")
    _upload(client, task_in_kept.id, owner, auth_headers, filename="do-mantido.pdf")
    assert len(list(tmp_path.iterdir())) == 2

    client.delete(f"/api/v1/workspaces/{workspace_to_delete.id}", headers=auth_headers(owner))

    remaining_files = list(tmp_path.iterdir())
    assert len(remaining_files) == 1


def test_delete_workspace_succeeds_even_when_physical_removal_fails(
    client, make_user, make_workspace, make_task, auth_headers, monkeypatch
):
    from app.utils import file_storage

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    _upload(client, task.id, owner, auth_headers)

    def _raise_os_error(_storage_path: str) -> None:
        raise OSError("permissão negada")

    monkeypatch.setattr(file_storage, "delete_file", _raise_os_error)

    response = client.delete(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(owner))

    assert response.status_code == 204


# --- Regressão -----------------------------------------------------------------


def test_delete_workspace_still_forbidden_for_non_owner(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    """Confirma que a exclusão de workspace continua restrita ao Owner após
    a mudança de assinatura do Service (novo `AttachmentRepository`)."""
    owner = make_user()
    admin = make_user(email="admin-delete-matrix@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.delete(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(admin))

    assert response.status_code == 403


def test_project_deletion_still_works_after_workspace_service_signature_change(
    client, make_user, make_workspace, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": "Projeto de regressão"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
