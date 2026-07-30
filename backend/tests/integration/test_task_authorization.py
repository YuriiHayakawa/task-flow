"""T077 [US5] — validação isolada das dependencies de autorização de tarefa,
antes das Routes existirem: chamadas diretas (sem HTTP), contra o banco real,
cobrindo a matriz de "Visibilidade versus Participação" (research.md #8,
plan.md — Permissões de Edição e Exclusão)."""

import uuid

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.dependencies.task_authorization import (
    require_task_delete,
    require_task_editor,
    require_task_participant,
    require_task_visible,
)
from app.enums.workspace_role import WorkspaceRole


# --- require_task_visible ----------------------------------------------------


def test_visible_personal_task_creator(db_session, make_user, make_task):
    creator = make_user()
    task = make_task(creator=creator)

    result = require_task_visible(task.id, current_user=creator, db=db_session)

    assert result.id == task.id


def test_visible_personal_task_other_user_raises_not_found(db_session, make_user, make_task):
    creator = make_user()
    other = make_user(email="other-visible@example.com")
    task = make_task(creator=creator)

    with pytest.raises(NotFoundError):
        require_task_visible(task.id, current_user=other, db=db_session)


@pytest.mark.parametrize("role", [WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])
def test_visible_workspace_task_any_member_role(
    db_session, make_user, make_workspace, add_workspace_member, make_task, role
):
    owner = make_user()
    viewer = make_user(email=f"viewer-{role.value}@example.com")
    workspace = make_workspace(owner=owner)
    if role != WorkspaceRole.OWNER:
        add_workspace_member(workspace=workspace, user=viewer, role=role)
    else:
        viewer = owner
    task = make_task(creator=owner, workspace=workspace)

    result = require_task_visible(task.id, current_user=viewer, db=db_session)

    assert result.id == task.id


def test_visible_workspace_task_outsider_raises_not_found(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    outsider = make_user(email="outsider-visible@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    with pytest.raises(NotFoundError):
        require_task_visible(task.id, current_user=outsider, db=db_session)


def test_visible_nonexistent_task_raises_not_found(db_session, make_user):
    user = make_user()

    with pytest.raises(NotFoundError):
        require_task_visible(uuid.uuid4(), current_user=user, db=db_session)


# --- require_task_participant -------------------------------------------------


def test_participant_personal_task_creator_ok(db_session, make_user, make_task):
    creator = make_user()
    task = make_task(creator=creator)

    result = require_task_participant(
        task=require_task_visible(task.id, current_user=creator, db=db_session),
        current_user=creator,
        db=db_session,
    )

    assert result.id == task.id


def test_participant_workspace_task_assignee_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    assignee = make_user(email="assignee-participant@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    result = require_task_participant(
        task=require_task_visible(task.id, current_user=assignee, db=db_session),
        current_user=assignee,
        db=db_session,
    )

    assert result.id == task.id


def test_participant_workspace_task_explicit_member_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    from app.models.task_member import TaskMember

    owner = make_user()
    participant = make_user(email="explicit-participant@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    result = require_task_participant(
        task=require_task_visible(task.id, current_user=participant, db=db_session),
        current_user=participant,
        db=db_session,
    )

    assert result.id == task.id


def test_participant_workspace_task_member_without_participation_forbidden(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    member = make_user(email="non-participant-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    with pytest.raises(ForbiddenError):
        require_task_participant(
            task=require_task_visible(task.id, current_user=member, db=db_session),
            current_user=member,
            db=db_session,
        )


def test_participant_workspace_task_admin_without_participation_forbidden(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    """research.md #8: Owner/Admin MUST NOT ser participantes automáticos só
    por deterem essas roles."""
    owner = make_user()
    admin = make_user(email="admin-non-participant@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    task = make_task(creator=owner, workspace=workspace)

    with pytest.raises(ForbiddenError):
        require_task_participant(
            task=require_task_visible(task.id, current_user=admin, db=db_session),
            current_user=admin,
            db=db_session,
        )


def test_participant_workspace_task_outsider_raises_not_found(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    outsider = make_user(email="outsider-participant@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    with pytest.raises(NotFoundError):
        require_task_participant(
            task=require_task_visible(task.id, current_user=outsider, db=db_session),
            current_user=outsider,
            db=db_session,
        )


# --- require_task_editor -------------------------------------------------


def test_editor_personal_task_creator_ok(db_session, make_user, make_task):
    creator = make_user()
    task = make_task(creator=creator)

    result = require_task_editor(
        task=require_task_visible(task.id, current_user=creator, db=db_session),
        current_user=creator,
        db=db_session,
    )

    assert result.id == task.id


def test_editor_personal_task_other_user_raises_not_found(db_session, make_user, make_task):
    creator = make_user()
    other = make_user(email="other-editor@example.com")
    task = make_task(creator=creator)

    with pytest.raises(NotFoundError):
        require_task_editor(
            task=require_task_visible(task.id, current_user=other, db=db_session),
            current_user=other,
            db=db_session,
        )


def test_editor_workspace_task_creator_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    creator = make_user(email="creator-editor@example.com")
    assignee = make_user(email="assignee-editor@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace)

    result = require_task_editor(
        task=require_task_visible(task.id, current_user=creator, db=db_session),
        current_user=creator,
        db=db_session,
    )

    assert result.id == task.id


def test_editor_workspace_task_assignee_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    creator = make_user(email="creator-editor2@example.com")
    assignee = make_user(email="assignee-editor2@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace)

    result = require_task_editor(
        task=require_task_visible(task.id, current_user=assignee, db=db_session),
        current_user=assignee,
        db=db_session,
    )

    assert result.id == task.id


@pytest.mark.parametrize("role", [WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
def test_editor_workspace_task_owner_or_admin_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task, role
):
    owner = make_user()
    creator = make_user(email=f"creator-editor-{role.value}@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)
    editor_user = owner if role == WorkspaceRole.OWNER else make_user(email=f"admin-editor@example.com")
    if role == WorkspaceRole.ADMIN:
        add_workspace_member(workspace=workspace, user=editor_user, role=WorkspaceRole.ADMIN)

    result = require_task_editor(
        task=require_task_visible(task.id, current_user=editor_user, db=db_session),
        current_user=editor_user,
        db=db_session,
    )

    assert result.id == task.id


def test_editor_workspace_task_plain_member_forbidden(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    creator = make_user(email="creator-editor3@example.com")
    plain_member = make_user(email="plain-member-editor@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    with pytest.raises(ForbiddenError):
        require_task_editor(
            task=require_task_visible(task.id, current_user=plain_member, db=db_session),
            current_user=plain_member,
            db=db_session,
        )


# --- require_task_delete -------------------------------------------------


def test_delete_personal_task_creator_ok(db_session, make_user, make_task):
    creator = make_user()
    task = make_task(creator=creator)

    result = require_task_delete(
        task=require_task_visible(task.id, current_user=creator, db=db_session),
        current_user=creator,
        db=db_session,
    )

    assert result.id == task.id


def test_delete_workspace_task_creator_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    creator = make_user(email="creator-delete@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    result = require_task_delete(
        task=require_task_visible(task.id, current_user=creator, db=db_session),
        current_user=creator,
        db=db_session,
    )

    assert result.id == task.id


@pytest.mark.parametrize("role", [WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
def test_delete_workspace_task_owner_or_admin_ok(
    db_session, make_user, make_workspace, add_workspace_member, make_task, role
):
    owner = make_user()
    creator = make_user(email=f"creator-delete-{role.value}@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)
    deleter = owner if role == WorkspaceRole.OWNER else make_user(email="admin-delete@example.com")
    if role == WorkspaceRole.ADMIN:
        add_workspace_member(workspace=workspace, user=deleter, role=WorkspaceRole.ADMIN)

    result = require_task_delete(
        task=require_task_visible(task.id, current_user=deleter, db=db_session),
        current_user=deleter,
        db=db_session,
    )

    assert result.id == task.id


def test_delete_workspace_task_assignee_only_forbidden(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    """Distinção-chave vs `require_task_editor`: o responsável isolado (que
    não seja também o criador) MUST NOT excluir a tarefa."""
    owner = make_user()
    creator = make_user(email="creator-delete2@example.com")
    assignee = make_user(email="assignee-delete-only@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace)

    with pytest.raises(ForbiddenError):
        require_task_delete(
            task=require_task_visible(task.id, current_user=assignee, db=db_session),
            current_user=assignee,
            db=db_session,
        )


def test_delete_workspace_task_plain_member_forbidden(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    creator = make_user(email="creator-delete3@example.com")
    plain_member = make_user(email="plain-member-delete@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    with pytest.raises(ForbiddenError):
        require_task_delete(
            task=require_task_visible(task.id, current_user=plain_member, db=db_session),
            current_user=plain_member,
            db=db_session,
        )
