"""T098 [US10] — testes unitários de `AttachmentService`: validação de tipo/
tamanho antes de gravar em disco, fluxo de exclusão controlada (uploader ou
Owner/Admin), isolamento entre tarefas. Isolado do banco via repositories em
memória (Fake), no mesmo padrão de `tests/unit/test_checklist_item_service.py`.
As chamadas reais de `app.utils.file_storage` (grava/remove no disco) são
isoladas via `tmp_path`, nunca tocando `ATTACHMENTS_DIR` real."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import BusinessRuleViolationError, ForbiddenError, NotFoundError
from app.enums.workspace_role import WorkspaceRole
from app.models.attachment import Attachment
from app.models.task import Task
from app.models.user import User
from app.services.attachment_service import AttachmentService
from app.utils import file_storage


@pytest.fixture(autouse=True)
def _isolated_attachments_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ATTACHMENTS_DIR", str(tmp_path))
    return tmp_path


class _FakeSession:
    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


class FakeTaskRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.tasks: dict[uuid.UUID, Task] = {}

    def seed(self, *, creator_id: uuid.UUID, workspace_id: uuid.UUID | None = None) -> Task:
        task = Task(
            id=uuid.uuid4(),
            title="Tarefa",
            creator_id=creator_id,
            assignee_id=creator_id,
            workspace_id=workspace_id,
        )
        self.tasks[task.id] = task
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.tasks.get(task_id)


class FakeAttachmentRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.items: dict[uuid.UUID, Attachment] = {}
        self._uploader_info: dict[uuid.UUID, tuple[str, str]] = {}

    def seed(
        self,
        task_id: uuid.UUID,
        uploader: User,
        *,
        original_filename: str = "arquivo.pdf",
        content_type: str = "application/pdf",
        size_bytes: int = 10,
    ) -> Attachment:
        attachment = Attachment(
            id=uuid.uuid4(),
            task_id=task_id,
            uploaded_by_id=uploader.id,
            original_filename=original_filename,
            storage_path=f"{uuid.uuid4()}.pdf",
            content_type=content_type,
            size_bytes=size_bytes,
        )
        attachment.created_at = datetime.now(timezone.utc)
        self.items[attachment.id] = attachment
        self._uploader_info[attachment.id] = (uploader.name, uploader.email)
        return attachment

    def create(self, attachment: Attachment) -> Attachment:
        attachment.id = attachment.id or uuid.uuid4()
        attachment.created_at = datetime.now(timezone.utc)
        self.items[attachment.id] = attachment
        return attachment

    def list_by_task(self, task_id: uuid.UUID) -> list[SimpleNamespace]:
        items = sorted(
            (item for item in self.items.values() if item.task_id == task_id),
            key=lambda i: (i.created_at, i.id),
        )
        rows = []
        for item in items:
            name, email = self._uploader_info.get(item.id, ("Desconhecido", "desconhecido@example.com"))
            rows.append(
                SimpleNamespace(
                    id=item.id,
                    original_filename=item.original_filename,
                    content_type=item.content_type,
                    size_bytes=item.size_bytes,
                    uploaded_by_id=item.uploaded_by_id,
                    uploaded_by_name=name,
                    uploaded_by_email=email,
                    created_at=item.created_at,
                )
            )
        return rows

    def get_by_task_and_id(self, task_id: uuid.UUID, attachment_id: uuid.UUID) -> Attachment | None:
        item = self.items.get(attachment_id)
        if item is None or item.task_id != task_id:
            return None
        return item

    def delete(self, attachment: Attachment) -> None:
        self.items.pop(attachment.id, None)


class FakeWorkspaceMemberRepository:
    def __init__(self) -> None:
        self.roles: dict[tuple[uuid.UUID, uuid.UUID], WorkspaceRole] = {}

    def seed_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: WorkspaceRole) -> None:
        self.roles[(workspace_id, user_id)] = role

    def get_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole | None:
        return self.roles.get((workspace_id, user_id))


def _make_user(name: str = "Uploader", email: str = "uploader@example.com") -> User:
    return User(id=uuid.uuid4(), name=name, email=email, password_hash="hash")


@pytest.fixture()
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture()
def attachment_repo() -> FakeAttachmentRepository:
    return FakeAttachmentRepository()


@pytest.fixture()
def workspace_member_repo() -> FakeWorkspaceMemberRepository:
    return FakeWorkspaceMemberRepository()


@pytest.fixture()
def service(
    attachment_repo: FakeAttachmentRepository,
    task_repo: FakeTaskRepository,
    workspace_member_repo: FakeWorkspaceMemberRepository,
) -> AttachmentService:
    return AttachmentService(attachment_repo, task_repo, workspace_member_repo)


# --- list_attachments -------------------------------------------------------


def test_list_attachments_empty(service, task_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())

    assert service.list_attachments(task.id) == []


def test_list_attachments_multiple_preserves_order(service, task_repo, attachment_repo) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)
    attachment_repo.seed(task.id, uploader, original_filename="primeiro.pdf")
    attachment_repo.seed(task.id, uploader, original_filename="segundo.pdf")

    result = service.list_attachments(task.id)

    assert [item.original_filename for item in result] == ["primeiro.pdf", "segundo.pdf"]


def test_list_attachments_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.list_attachments(uuid.uuid4())


# --- create_attachment -------------------------------------------------------


def test_create_attachment_valid(service, task_repo, tmp_path) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)

    result = service.create_attachment(
        task.id,
        uploader,
        original_filename="documento.pdf",
        content_type="application/pdf",
        content=b"conteudo binario",
    )

    assert result.original_filename == "documento.pdf"
    assert result.content_type == "application/pdf"
    assert result.size_bytes == len(b"conteudo binario")
    assert result.uploaded_by_id == uploader.id
    assert result.uploaded_by_name == uploader.name
    assert result.uploaded_by_email == uploader.email
    # arquivo físico foi realmente gravado em disco:
    written_files = list(tmp_path.iterdir())
    assert len(written_files) == 1
    assert written_files[0].read_bytes() == b"conteudo binario"


def test_create_attachment_rejects_disallowed_content_type(service, task_repo, tmp_path) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)

    with pytest.raises(BusinessRuleViolationError):
        service.create_attachment(
            task.id,
            uploader,
            original_filename="virus.exe",
            content_type="application/x-msdownload",
            content=b"dados",
        )

    # nenhum arquivo foi gravado — validação ocorre antes da escrita em disco:
    assert list(tmp_path.iterdir()) == []


def test_create_attachment_rejects_oversized_file(service, task_repo, tmp_path) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)
    oversized_content = b"x" * (settings.ATTACHMENTS_MAX_SIZE_BYTES + 1)

    with pytest.raises(BusinessRuleViolationError):
        service.create_attachment(
            task.id,
            uploader,
            original_filename="grande.pdf",
            content_type="application/pdf",
            content=oversized_content,
        )

    assert list(tmp_path.iterdir()) == []


def test_create_attachment_nonexistent_task_raises_not_found(service) -> None:
    uploader = _make_user()

    with pytest.raises(NotFoundError):
        service.create_attachment(
            uuid.uuid4(),
            uploader,
            original_filename="x.pdf",
            content_type="application/pdf",
            content=b"dados",
        )


# --- get_download_target -----------------------------------------------------


def test_get_download_target_returns_path_filename_and_content_type(
    service, task_repo, attachment_repo, tmp_path
) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)
    attachment = attachment_repo.seed(task.id, uploader, original_filename="relatorio.pdf")

    file_path, original_filename, content_type = service.get_download_target(task.id, attachment.id)

    assert file_path == tmp_path / attachment.storage_path
    assert original_filename == "relatorio.pdf"
    assert content_type == "application/pdf"


def test_get_download_target_nonexistent_attachment_raises_not_found(service, task_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())

    with pytest.raises(NotFoundError):
        service.get_download_target(task.id, uuid.uuid4())


def test_get_download_target_from_another_task_raises_not_found(
    service, task_repo, attachment_repo
) -> None:
    uploader = _make_user()
    task_1 = task_repo.seed(creator_id=uploader.id)
    task_2 = task_repo.seed(creator_id=uploader.id)
    attachment = attachment_repo.seed(task_1.id, uploader)

    with pytest.raises(NotFoundError):
        service.get_download_target(task_2.id, attachment.id)


def test_get_download_target_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.get_download_target(uuid.uuid4(), uuid.uuid4())


# --- delete_attachment --------------------------------------------------------


def test_delete_attachment_by_uploader_removes_record_and_file(
    service, task_repo, attachment_repo, tmp_path
) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id, workspace_id=uuid.uuid4())
    attachment = attachment_repo.seed(task.id, uploader)
    physical_file = tmp_path / attachment.storage_path
    physical_file.write_bytes(b"dados")

    service.delete_attachment(task.id, attachment.id, uploader)

    assert attachment_repo.get_by_task_and_id(task.id, attachment.id) is None
    assert not physical_file.exists()


def test_delete_attachment_by_workspace_admin_removes_someone_elses_attachment(
    service, task_repo, attachment_repo, workspace_member_repo
) -> None:
    uploader = _make_user(name="Colaborador", email="colaborador@example.com")
    admin = _make_user(name="Admin", email="admin@example.com")
    workspace_id = uuid.uuid4()
    task = task_repo.seed(creator_id=uploader.id, workspace_id=workspace_id)
    attachment = attachment_repo.seed(task.id, uploader)
    workspace_member_repo.seed_role(workspace_id, admin.id, WorkspaceRole.ADMIN)

    service.delete_attachment(task.id, attachment.id, admin)

    assert attachment_repo.get_by_task_and_id(task.id, attachment.id) is None


def test_delete_attachment_by_workspace_owner_removes_someone_elses_attachment(
    service, task_repo, attachment_repo, workspace_member_repo
) -> None:
    uploader = _make_user(name="Colaborador", email="colaborador@example.com")
    owner = _make_user(name="Owner", email="owner@example.com")
    workspace_id = uuid.uuid4()
    task = task_repo.seed(creator_id=owner.id, workspace_id=workspace_id)
    attachment = attachment_repo.seed(task.id, uploader)
    workspace_member_repo.seed_role(workspace_id, owner.id, WorkspaceRole.OWNER)

    service.delete_attachment(task.id, attachment.id, owner)

    assert attachment_repo.get_by_task_and_id(task.id, attachment.id) is None


def test_delete_attachment_rejects_non_uploader_non_admin_member(
    service, task_repo, attachment_repo, workspace_member_repo
) -> None:
    uploader = _make_user()
    member = _make_user(name="Member", email="member@example.com")
    workspace_id = uuid.uuid4()
    task = task_repo.seed(creator_id=uploader.id, workspace_id=workspace_id)
    attachment = attachment_repo.seed(task.id, uploader)
    workspace_member_repo.seed_role(workspace_id, member.id, WorkspaceRole.MEMBER)

    with pytest.raises(ForbiddenError):
        service.delete_attachment(task.id, attachment.id, member)

    # o anexo permanece intacto:
    assert attachment_repo.get_by_task_and_id(task.id, attachment.id) is not None


def test_delete_attachment_on_personal_task_rejects_non_uploader(
    service, task_repo, attachment_repo
) -> None:
    """Tarefa pessoal (`workspace_id is None`) não tem Owner/Admin — só o
    uploader pode remover o próprio anexo."""
    uploader = _make_user()
    someone_else = _make_user(name="Outro", email="outro@example.com")
    task = task_repo.seed(creator_id=uploader.id, workspace_id=None)
    attachment = attachment_repo.seed(task.id, uploader)

    with pytest.raises(ForbiddenError):
        service.delete_attachment(task.id, attachment.id, someone_else)


def test_delete_attachment_nonexistent_raises_not_found(service, task_repo) -> None:
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)

    with pytest.raises(NotFoundError):
        service.delete_attachment(task.id, uuid.uuid4(), uploader)


def test_delete_attachment_from_another_task_raises_not_found(
    service, task_repo, attachment_repo
) -> None:
    uploader = _make_user()
    task_1 = task_repo.seed(creator_id=uploader.id)
    task_2 = task_repo.seed(creator_id=uploader.id)
    attachment = attachment_repo.seed(task_1.id, uploader)

    with pytest.raises(NotFoundError):
        service.delete_attachment(task_2.id, attachment.id, uploader)

    assert attachment_repo.get_by_task_and_id(task_1.id, attachment.id) is not None


def test_delete_attachment_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.delete_attachment(uuid.uuid4(), uuid.uuid4(), _make_user())


def test_delete_attachment_logs_error_without_failing_when_physical_removal_fails(
    service, task_repo, attachment_repo, monkeypatch
) -> None:
    """research.md #12: falha ao remover o arquivo físico é logada como
    `ERROR`, mas a exclusão do registro (já commitada) não é revertida nem a
    exceção propagada ao chamador — o estado autoritativo (banco) já está
    correto."""
    uploader = _make_user()
    task = task_repo.seed(creator_id=uploader.id)
    attachment = attachment_repo.seed(task.id, uploader)

    def _raise_os_error(_storage_path: str) -> None:
        raise OSError("permissão negada")

    monkeypatch.setattr(file_storage, "delete_file", _raise_os_error)

    service.delete_attachment(task.id, attachment.id, uploader)  # não deve levantar

    assert attachment_repo.get_by_task_and_id(task.id, attachment.id) is None
