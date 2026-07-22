import uuid

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessRuleViolationError, ConflictError, NotFoundError
from app.models.task import Task
from app.models.task_member import TaskMember
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.task_member import TaskMemberRead


class TaskMemberService:
    """FR-030 a FR-034. Segue o mesmo padrão de `WorkspaceMemberService`/
    `ProjectService`: os métodos recebem IDs (não objetos ORM pré-carregados
    pela rota) e resolvem tudo que precisam via repository — quem autoriza o
    chamador é a dependency (`require_task_editor`, T077), quem valida as
    regras de domínio sobre a tarefa/participante é este Service."""

    def __init__(
        self,
        task_member_repository: TaskMemberRepository,
        task_repository: TaskRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        user_repository: UserRepository,
    ) -> None:
        self.task_member_repository = task_member_repository
        self.task_repository = task_repository
        self.workspace_member_repository = workspace_member_repository
        self.user_repository = user_repository
        self.db = task_member_repository.db

    def _get_task_or_404(self, task_id: uuid.UUID) -> Task:
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    def list_members(self, task_id: uuid.UUID) -> list[TaskMemberRead]:
        """FR-033: o responsável é sempre participante implícito — inclusive
        numa tarefa pessoal, onde ele é o próprio criador (data-model.md: "a
        query de participantes de tarefa pessoal sempre retorna apenas o
        criador") — nenhuma linha física é criada para representá-lo.

        Ordenação (não definida pelo contrato — decisão documentada aqui,
        sem alterar o contrato): responsável primeiro, depois participantes
        explícitos por `(added_at, user_id)`, determinístico. Se o
        responsável também tiver uma linha explícita em `TaskMember` (ex.:
        foi adicionado antes de se tornar responsável), seu `added_at` real é
        preservado — nunca forçado a `None` nesse caso; `None` é usado
        apenas quando não existe linha nenhuma para ele."""
        task = self._get_task_or_404(task_id)

        explicit_rows = (
            self.task_member_repository.list_by_task(task_id)
            if task.workspace_id is not None
            else []
        )
        explicit_members = [
            TaskMemberRead(user_id=row.user_id, name=row.name, email=row.email, added_at=row.added_at)
            for row in explicit_rows
        ]

        assignee_entry = next(
            (member for member in explicit_members if member.user_id == task.assignee_id), None
        )
        if assignee_entry is None:
            assignee = self.user_repository.get_by_id(task.assignee_id)
            assert assignee is not None  # FK RESTRICT garante que sempre existe
            assignee_entry = TaskMemberRead(
                user_id=assignee.id, name=assignee.name, email=assignee.email, added_at=None
            )

        others = sorted(
            (member for member in explicit_members if member.user_id != task.assignee_id),
            key=lambda member: (member.added_at, member.user_id),
        )
        return [assignee_entry, *others]

    def add_member(self, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskMemberRead:
        """FR-030 a FR-032. "Usuário inexistente" e "usuário existente mas
        não membro do workspace" produzem o mesmo `400` — mesma convenção já
        estabelecida em `TaskService.create` (Fase 6/T072): `get_role`
        retorna `None` de forma idêntica para os dois casos, sem distinção
        proposital (o contrato não os diferencia)."""
        task = self._get_task_or_404(task_id)

        if task.workspace_id is None:
            raise BusinessRuleViolationError("Tarefas pessoais não podem ter participantes.")

        role = self.workspace_member_repository.get_role(task.workspace_id, user_id)
        if role is None:
            raise BusinessRuleViolationError(
                "O participante deve ser membro do mesmo workspace da tarefa."
            )

        if user_id == task.assignee_id or self.task_member_repository.exists(task_id, user_id):
            raise ConflictError("Este usuário já é participante da tarefa.")

        member = TaskMember(task_id=task_id, user_id=user_id)
        try:
            self.task_member_repository.create(member)
            self.db.commit()
        except IntegrityError:
            # Última linha de defesa do UNIQUE(task_id, user_id): corrida
            # entre o `exists()` acima e a escrita. Tratada como o mesmo
            # conflito de duplicidade já documentado, nunca como erro 500.
            self.db.rollback()
            raise ConflictError("Este usuário já é participante da tarefa.") from None

        self.db.refresh(member)
        user = self.user_repository.get_by_id(user_id)
        assert user is not None
        return TaskMemberRead(
            user_id=user.id, name=user.name, email=user.email, added_at=member.created_at
        )

    def remove_member(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """FR-034: remove somente a linha de `TaskMember` — nunca a tarefa, o
        usuário, comentários, anexos ou histórico (nenhum desses é sequer
        referenciado aqui)."""
        task = self._get_task_or_404(task_id)

        if task.workspace_id is None:
            raise BusinessRuleViolationError("Tarefas pessoais não podem ter participantes.")

        if user_id == task.assignee_id:
            raise BusinessRuleViolationError(
                "O responsável não pode ser removido como participante — reatribua a tarefa primeiro."
            )

        member = self.task_member_repository.get_by_task_and_user(task_id, user_id)
        if member is None:
            raise NotFoundError("Participante não encontrado nesta tarefa.")

        self.task_member_repository.delete(member)
        self.db.commit()
