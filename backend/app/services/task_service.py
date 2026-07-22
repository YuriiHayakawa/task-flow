import uuid
from datetime import datetime, timezone

from app.core.exceptions import BusinessRuleViolationError, ForbiddenError, NotFoundError
from app.enums.task_status import TaskStatus
from app.models.task import Task
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        workspace_member_repository: WorkspaceMemberRepository,
    ) -> None:
        self.task_repository = task_repository
        self.project_repository = project_repository
        self.workspace_member_repository = workspace_member_repository
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
            assignee_id = self._resolve_workspace_assignee(data, workspace_id, creator_id)

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

        return workspace_id, data.project_id

    def _resolve_workspace_assignee(
        self, data: TaskCreate, workspace_id: uuid.UUID, creator_id: uuid.UUID
    ) -> uuid.UUID:
        """FR-021: qualquer membro do workspace pode ser responsável. Sem
        `assignee_id`, o próprio criador assume — já confirmado membro por
        `_resolve_workspace_and_project`, sem precisar reconsultar."""
        if data.assignee_id is None or data.assignee_id == creator_id:
            return creator_id

        role = self.workspace_member_repository.get_role(workspace_id, data.assignee_id)
        if role is None:
            raise BusinessRuleViolationError(
                "O responsável pela tarefa deve ser membro deste workspace."
            )
        return data.assignee_id

    def list_personal_tasks(self, creator_id: uuid.UUID) -> list[Task]:
        return self.task_repository.list_personal_by_creator(creator_id)

    def get_personal_task_or_404(self, task_id: uuid.UUID, creator_id: uuid.UUID) -> Task:
        """Tarefa pessoal MUST ser visível/editável somente pelo próprio criador
        (data-model.md, invariantes de tarefa pessoal) — qualquer outro caso
        (não existe, é de workspace, ou pertence a outro usuário) é 404, nunca
        403, para não confirmar a existência do recurso a quem não tem acesso."""
        task = self.task_repository.get_by_id(task_id)
        if task is None or task.workspace_id is not None or task.creator_id != creator_id:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    def update(self, task: Task, data: TaskUpdate) -> Task:
        """`status = DONE` seta `completed_at`; reabrir limpa (FR-011). Conversão
        de tarefa pessoal para tarefa de workspace ainda não é suportada nesta
        fase (chega com a lógica completa de workspace na US4)."""
        changes = data.model_dump(exclude_unset=True)

        if "workspace_id" in changes or "project_id" in changes:
            raise BusinessRuleViolationError(
                "Vincular esta tarefa a um workspace/projeto ainda não é suportado."
            )

        if "assignee_id" in changes:
            new_assignee_id = changes["assignee_id"]
            if new_assignee_id is not None and new_assignee_id != task.creator_id:
                raise BusinessRuleViolationError(
                    "Uma tarefa pessoal não pode ser atribuída a outro usuário."
                )
            changes["assignee_id"] = task.creator_id

        if "status" in changes:
            new_status = changes["status"]
            if new_status == TaskStatus.DONE and task.status != TaskStatus.DONE:
                task.completed_at = datetime.now(timezone.utc)
            elif new_status != TaskStatus.DONE and task.status == TaskStatus.DONE:
                task.completed_at = None

        for field, value in changes.items():
            setattr(task, field, value)

        task = self.task_repository.update(task)
        self.db.commit()
        self.db.refresh(task)
        return task
