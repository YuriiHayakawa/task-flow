import uuid
from datetime import datetime, timezone

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.enums.task_status import TaskStatus
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, task_repository: TaskRepository) -> None:
        self.task_repository = task_repository
        self.db = task_repository.db

    def create(self, data: TaskCreate, creator_id: uuid.UUID) -> Task:
        """FR-006/FR-007/FR-029/FR-031: regras de tarefa pessoal. A derivação de
        workspace a partir de projeto e a validação de membership chegam na US4
        (T072) — aqui só o caminho sem workspace/projeto é processado."""
        if data.project_id is not None and data.workspace_id is None:
            raise BusinessRuleViolationError(
                "Uma tarefa com projeto deve também informar o workspace."
            )

        if data.workspace_id is None:
            # Tarefa pessoal: o responsável é sempre o próprio criador — nunca
            # pode ser atribuída a outro usuário (invariante de tarefa pessoal).
            if data.assignee_id is not None and data.assignee_id != creator_id:
                raise BusinessRuleViolationError(
                    "Uma tarefa pessoal não pode ser atribuída a outro usuário."
                )
            assignee_id = creator_id
        else:
            # Tarefa de workspace: validação completa de membership chega na US4.
            assignee_id = data.assignee_id or creator_id

        task = Task(
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            assignee_id=assignee_id,
            creator_id=creator_id,
            workspace_id=data.workspace_id,
            project_id=data.project_id,
        )
        task = self.task_repository.create(task)
        self.db.commit()
        self.db.refresh(task)
        return task

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
