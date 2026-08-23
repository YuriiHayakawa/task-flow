import uuid
from datetime import datetime, timezone
from enum import Enum

from app.core.exceptions import BusinessRuleViolationError, ForbiddenError
from app.core.logging import get_logger
from app.enums.notification_type import NotificationType
from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.models.notification import Notification
from app.models.task import Task
from app.models.task_history_entry import TaskHistoryEntry
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_history_repository import TaskHistoryRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.task import TaskCreate, TaskSearchParams, TaskUpdate
from app.utils import file_storage

logger = get_logger(__name__)

_TASK_CHANGED_TRACKED_FIELDS = ("status", "priority", "due_date", "assignee_id")


def _serialize_history_value(value: object) -> str | None:
    """`TaskHistoryEntry.old_value`/`new_value` são `string` (data-model.md
    — "representação textual"). Enums usam `.value` (ex.: `"DONE"`, não
    `"TaskStatus.DONE"`); `date`/`UUID` já têm `str()` legível (ISO 8601,
    UUID padrão)."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    return str(value)


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        task_member_repository: TaskMemberRepository,
        notification_repository: NotificationRepository,
        task_history_repository: TaskHistoryRepository,
        attachment_repository: AttachmentRepository,
        project_member_repository: ProjectMemberRepository,
    ) -> None:
        self.task_repository = task_repository
        self.project_repository = project_repository
        self.workspace_member_repository = workspace_member_repository
        self.task_member_repository = task_member_repository
        self.notification_repository = notification_repository
        self.task_history_repository = task_history_repository
        self.attachment_repository = attachment_repository
        self.project_member_repository = project_member_repository
        self.db = task_repository.db

    def create(self, data: TaskCreate, creator_id: uuid.UUID) -> Task:
        """FR-006 a FR-008, FR-021, FR-029, FR-031 (US4/T072): tarefa pessoal,
        de workspace direto, ou de projeto — toda a derivação/validação abaixo
        ocorre antes de qualquer persistência, e um único `commit()` fecha a
        transação (nenhuma escrita parcial em caso de erro)."""
        if data.workspace_id is None and data.project_id is None:
            workspace_id: uuid.UUID | None = None
            project_id: uuid.UUID | None = None
            assignee_id = self._resolve_personal_assignee(data, creator_id)
        else:
            workspace_id, project_id = self._resolve_workspace_and_project(data, creator_id)
            assignee_id = self._resolve_workspace_assignee(data, workspace_id, project_id, creator_id)

        task = Task(
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            assignee_id=assignee_id,
            creator_id=creator_id,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        task = self.task_repository.create(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def _resolve_personal_assignee(self, data: TaskCreate, creator_id: uuid.UUID) -> uuid.UUID:
        """Invariante de tarefa pessoal (data-model.md): o responsável é
        sempre o próprio criador — nunca pode ser atribuída a outro usuário."""
        if data.assignee_id is not None and data.assignee_id != creator_id:
            raise BusinessRuleViolationError(
                "Uma tarefa pessoal não pode ser atribuída a outro usuário."
            )
        return creator_id

    def _resolve_workspace_and_project(
        self, data: TaskCreate, creator_id: uuid.UUID
    ) -> tuple[uuid.UUID, uuid.UUID | None]:
        """FR-008: se `project_id` for informado, deriva/valida o `workspace_id`
        a partir dele; em seguida confirma que o criador é membro do workspace
        resultante (`403` — contracts/projects-and-tasks.md trata isso como
        autorização, não como recurso oculto, já que o próprio chamador
        forneceu o `workspace_id`/`project_id` no corpo da requisição).

        Um `project_id` que não existe é tratado com o mesmo `403` de "criador
        não é membro" — nenhum dos dois casos confirma ao chamador se o
        projeto existe, mesma postura de segurança usada para `workspace_id`
        inexistente (`get_role` retorna `None` de forma idêntica para
        "workspace inexistente" e "workspace existe mas não sou membro" — não
        há distinção proposital entre os dois)."""
        if data.project_id is not None:
            project = self.project_repository.get_by_id(data.project_id)
            if project is None:
                raise ForbiddenError("Você não tem permissão para criar tarefas neste projeto.")

            if data.workspace_id is not None and data.workspace_id != project.workspace_id:
                raise BusinessRuleViolationError(
                    "O projeto informado não pertence ao workspace informado."
                )

            workspace_id = project.workspace_id
        else:
            assert data.workspace_id is not None  # garantido pelo caller
            workspace_id = data.workspace_id

        role = self.workspace_member_repository.get_role(workspace_id, creator_id)
        if role is None:
            raise ForbiddenError("Você não é membro deste workspace.")

        # Nota deliberada: criar uma tarefa DENTRO de um projeto restrito
        # exige só membership de WORKSPACE (FR-008, inalterado) — FR-009 só
        # restringe quem pode ser RESPONSÁVEL pela tarefa, não quem pode
        # criá-la; essa restrição é aplicada em `_resolve_workspace_assignee`
        # (inclusive no caminho padrão "sem assignee_id, o criador assume"),
        # nunca aqui.

        return workspace_id, data.project_id

    def _require_workspace_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Extraído de `_resolve_workspace_assignee` para ser reaproveitado
        também pela validação de reatribuição em `update` (T106) — mesma
        regra, mesma mensagem, um único lugar."""
        role = self.workspace_member_repository.get_role(workspace_id, user_id)
        if role is None:
            raise BusinessRuleViolationError(
                "O responsável pela tarefa deve ser membro deste workspace."
            )

    def _require_project_access(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """FR-009 (003-membros-projeto): dentro de um projeto restrito, só
        quem tem acesso a esse projeto pode ser responsável por uma tarefa
        dele — mesma fórmula de acesso da visibilidade (data-model.md):
        Owner do workspace, ou membro explícito do projeto. Aplicada tanto
        a um `assignee_id` explícito quanto ao caminho padrão em que o
        próprio criador assume (`_resolve_workspace_assignee`)."""
        role = self.workspace_member_repository.get_role(workspace_id, user_id)
        if role == WorkspaceRole.OWNER:
            return
        if not self.project_member_repository.is_member(project_id, user_id):
            raise BusinessRuleViolationError(
                "O responsável pela tarefa deve ser membro deste projeto."
            )

    def _resolve_workspace_assignee(
        self,
        data: TaskCreate,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None,
        creator_id: uuid.UUID,
    ) -> uuid.UUID:
        """FR-021: qualquer membro do workspace pode ser responsável — MAS,
        quando a tarefa pertence a um projeto restrito (003-membros-
        projeto/FR-009), o responsável também precisa ter acesso a esse
        projeto (`_require_project_access`). Sem `assignee_id`, o próprio
        criador assume — já confirmado membro do workspace por
        `_resolve_workspace_and_project`, mas AINDA precisa ser checado
        contra o projeto aqui: criar sem informar responsável não é uma
        forma de contornar FR-009."""
        if data.assignee_id is None or data.assignee_id == creator_id:
            if project_id is not None:
                self._require_project_access(workspace_id, project_id, creator_id)
            return creator_id

        self._require_workspace_member(workspace_id, data.assignee_id)
        if project_id is not None:
            self._require_project_access(workspace_id, project_id, data.assignee_id)
        return data.assignee_id

    def search(self, user_id: uuid.UUID, params: TaskSearchParams) -> tuple[list[Task], int]:
        """FR-055 a FR-059 (US8): endpoint central de listagem — tarefas
        pessoais do usuário + tarefas de todos os workspaces dos quais
        participa (mesma união já usada no dashboard desde a Fase 5/T065).

        003-membros-projeto: `owner_workspace_ids`/`member_project_ids`
        (research.md #2) resolvem a visibilidade extra de tarefas de
        projetos restritos — calculados aqui, nunca dentro da query
        (Constitution IV)."""
        workspace_ids = self.workspace_member_repository.list_workspace_ids_for_user(user_id)
        owner_workspace_ids = self.workspace_member_repository.list_owned_workspace_ids_for_user(
            user_id
        )
        member_project_ids = self.project_member_repository.list_project_ids_for_user(user_id)
        return self.task_repository.search(
            creator_id=user_id,
            workspace_ids=workspace_ids,
            owner_workspace_ids=owner_workspace_ids,
            member_project_ids=member_project_ids,
            search=params.search,
            status=params.status,
            priority=params.priority,
            workspace_id=params.workspace_id,
            project_id=params.project_id,
            assignee_id=params.assignee_id,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            page=params.page,
            page_size=params.page_size,
        )

    def delete(self, task: Task) -> None:
        """FR-005 (US1)/refinamento #7 (US5): a autorização (criador, ou
        Owner/Admin do workspace — `require_task_delete`, T077) já ocorreu
        na dependency da rota; aqui só a exclusão em si. Cascade de banco
        (`ON DELETE CASCADE`, já definido nas migrações da Fase 2) remove
        `TaskMember`/`Comment`/`ChecklistItem`/`Attachment`/
        `TaskHistoryEntry`/`Notification` relacionados.

        Fase 16 (hardening) — exclusão controlada de anexos (research.md
        #12): coleta os `storage_path` de todos os anexos da tarefa ANTES
        do cascade; só depois do `commit()` bem-sucedido remove os arquivos
        físicos — se a remoção física de algum falhar, loga `ERROR` sem
        falhar a resposta (o estado autoritativo, o banco, já está correto)."""
        task_id = task.id
        storage_paths = self.attachment_repository.list_storage_paths_by_task(task_id)

        self.task_repository.delete(task)
        self.db.commit()

        for storage_path in storage_paths:
            try:
                file_storage.delete_file(storage_path)
            except OSError:
                logger.error(
                    "Falha ao remover arquivo físico de anexo após exclusão de tarefa: "
                    "task_id=%s storage_path=%s",
                    task_id,
                    storage_path,
                )

    def update(self, task: Task, data: TaskUpdate, changed_by: uuid.UUID) -> Task:
        """`status = DONE` seta `completed_at`; reabrir limpa (FR-011).
        Conversão de tarefa pessoal para tarefa de workspace ainda não é
        suportada nesta fase.

        Reatribuição de responsável (T106 — correção de um bug encontrado na
        abertura da Fase 13): tarefa pessoal continua exigindo
        `assignee_id == creator_id` (única invariante válida ali); tarefa de
        workspace agora valida `assignee_id` contra membership do workspace
        (`_require_workspace_member`, mesma regra de `_resolve_workspace_
        assignee` em `create`) — ANTES desta correção, qualquer reatribuição
        de tarefa de workspace era incorretamente rejeitada pela regra de
        tarefa pessoal, aplicada aqui de forma incondicional.

        FR-039/T106: mudança de status/prioridade/prazo/responsável gera
        `Notification` tipo `TASK_CHANGED` para os participantes afetados
        (responsável anterior + responsável novo + `TaskMember` explícitos),
        exceto quem fez a alteração — tarefa pessoal nunca tem outro
        participante, então o conjunto é sempre vazio nesse caso.
        `due_soon_notified_for` é resetado para `NULL` sempre que `due_date`
        muda de fato (research.md #2), independentemente do valor anterior.

        FR-041/T110 (US12): os mesmos campos rastreados para `TASK_CHANGED`
        geram, cada um, uma `TaskHistoryEntry` (campo, valor anterior, novo
        valor, autor) — inclusive em tarefa pessoal (histórico não depende
        de haver outro participante, ao contrário da notificação).

        Transação única: `task.update` + todas as `Notification` + todas as
        `TaskHistoryEntry` num único `commit()`; qualquer exceção após o
        início das escritas reverte tudo (mesmo padrão de
        `CommentService.create_comment`, Fase 8)."""
        changes = data.model_dump(exclude_unset=True)

        if "workspace_id" in changes or "project_id" in changes:
            raise BusinessRuleViolationError(
                "Vincular esta tarefa a um workspace/projeto ainda não é suportado."
            )

        if "assignee_id" in changes:
            new_assignee_id = changes["assignee_id"]
            if task.workspace_id is None:
                if new_assignee_id is not None and new_assignee_id != task.creator_id:
                    raise BusinessRuleViolationError(
                        "Uma tarefa pessoal não pode ser atribuída a outro usuário."
                    )
                changes["assignee_id"] = task.creator_id
            elif new_assignee_id is None:
                changes["assignee_id"] = task.assignee_id
            else:
                self._require_workspace_member(task.workspace_id, new_assignee_id)
                if task.project_id is not None:
                    self._require_project_access(task.workspace_id, task.project_id, new_assignee_id)

        if "status" in changes:
            new_status = changes["status"]
            if new_status == TaskStatus.DONE and task.status != TaskStatus.DONE:
                task.completed_at = datetime.now(timezone.utc)
            elif new_status != TaskStatus.DONE and task.status == TaskStatus.DONE:
                task.completed_at = None

        if "due_date" in changes and changes["due_date"] != task.due_date:
            task.due_soon_notified_for = None

        changed_tracked_fields = [
            field
            for field in _TASK_CHANGED_TRACKED_FIELDS
            if field in changes and changes[field] != getattr(task, field)
        ]
        old_values = {field: getattr(task, field) for field in changed_tracked_fields}

        notification_recipients: set[uuid.UUID] = set()
        if changed_tracked_fields:
            old_assignee_id = task.assignee_id
            new_assignee_id = changes.get("assignee_id", task.assignee_id)
            notification_recipients = self._resolve_task_changed_recipients(
                task, old_assignee_id, new_assignee_id, changed_by
            )

        for field, value in changes.items():
            setattr(task, field, value)

        try:
            self.task_repository.update(task)
            for recipient_id in notification_recipients:
                notification = Notification(
                    recipient_id=recipient_id,
                    task_id=task.id,
                    type=NotificationType.TASK_CHANGED,
                    title="Tarefa atualizada",
                    message=f'A tarefa "{task.title}" foi atualizada.',
                )
                self.notification_repository.create(notification)
            for field in changed_tracked_fields:
                history_entry = TaskHistoryEntry(
                    task_id=task.id,
                    changed_by_id=changed_by,
                    field_changed=field,
                    old_value=_serialize_history_value(old_values[field]),
                    new_value=_serialize_history_value(changes[field]),
                )
                self.task_history_repository.create(history_entry)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(task)
        return task

    def _resolve_task_changed_recipients(
        self,
        task: Task,
        old_assignee_id: uuid.UUID,
        new_assignee_id: uuid.UUID,
        changed_by: uuid.UUID,
    ) -> set[uuid.UUID]:
        """Participantes afetados por uma alteração relevante (FR-039): o
        responsável anterior e o novo (cobre a própria reatribuição) +
        participantes explícitos (`TaskMember`) — exceto quem fez a
        alteração."""
        if task.workspace_id is None:
            return set()

        explicit_participant_ids = {
            row.user_id for row in self.task_member_repository.list_by_task(task.id)
        }
        return ({old_assignee_id, new_assignee_id} | explicit_participant_ids) - {changed_by}
