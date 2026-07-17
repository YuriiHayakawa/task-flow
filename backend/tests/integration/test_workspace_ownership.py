"""T053/T054 [US3] — transferência de Owner: API básica, concorrência real
(`SELECT ... FOR UPDATE`) e violação do índice único parcial de Owner.

Cobre: FR-013, FR-014, FR-019, research.md #20.

Os testes de concorrência (`Test*Concurrency*`) MUST usar conexões
independentes reais (não a `db_session` compartilhada da API), pois o
objetivo é exercitar o bloqueio pessimista de fato — duas requisições através
do `client` de teste compartilhariam a mesma transação/conexão e nunca
bloqueariam uma à outra."""

import threading
import time
import uuid

from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.enums.workspace_role import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.workspace_member_service import WorkspaceMemberService

# --- Testes via API (contrato HTTP básico) -----------------------------------


def test_transfer_ownership_success(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    new_owner = make_user(email="new-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=new_owner, role=WorkspaceRole.MEMBER)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/transfer-ownership",
        json={"new_owner_user_id": str(new_owner.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["my_role"] == "ADMIN"  # o Owner que chamou agora é Admin


def test_transfer_ownership_rejects_non_member_target(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-transfer@example.com")
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/transfer-ownership",
        json={"new_owner_user_id": str(outsider.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_transfer_ownership_forbidden_for_non_owner(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-transfer@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/transfer-ownership",
        json={"new_owner_user_id": str(admin.id)},
        headers=auth_headers(admin),
    )

    assert response.status_code == 403


# --- Teste de violação do índice único parcial de Owner ----------------------


def test_second_owner_row_violates_unique_partial_index(client, make_user, make_workspace, db_session):
    owner = make_user()
    other = make_user(email="second-owner@example.com")
    workspace = make_workspace(owner=owner)

    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=other.id, role=WorkspaceRole.MEMBER))
    db_session.flush()

    # Tenta forçar, por fora do Service, um segundo OWNER no mesmo workspace —
    # deve violar `ux_workspace_members_one_owner` (data-model.md). Usa um
    # SAVEPOINT (`begin_nested`) para isolar a falha esperada sem perturbar a
    # transação externa gerenciada pela fixture `db_session`.
    raised = False
    try:
        with db_session.begin_nested():
            db_session.execute(
                text(
                    "UPDATE workspace_members SET role = 'OWNER' "
                    "WHERE workspace_id = :workspace_id AND user_id = :user_id"
                ),
                {"workspace_id": str(workspace.id), "user_id": str(other.id)},
            )
    except IntegrityError:
        raised = True

    assert raised, "esperava IntegrityError do índice único parcial ao criar um segundo OWNER"


# --- Testes de concorrência real (conexões independentes) -------------------


def _setup_committed_workspace_with_owner() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Cria owner, candidato a novo owner e workspace numa transação própria,
    e faz commit de verdade — precisa estar visível para as conexões
    independentes usadas pelos testes de concorrência abaixo."""
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as connection:
        owner_id = uuid.uuid4()
        candidate_id = uuid.uuid4()
        workspace_id = uuid.uuid4()

        connection.execute(
            insert(User),
            [
                {
                    "id": owner_id,
                    "name": "Owner Concorrencia",
                    "email": f"owner-concurrency-{owner_id}@example.com",
                    "password_hash": hash_password("supersecret123"),
                    "is_active": True,
                    "is_system_admin": False,
                },
                {
                    "id": candidate_id,
                    "name": "Candidato Concorrencia",
                    "email": f"candidate-concurrency-{candidate_id}@example.com",
                    "password_hash": hash_password("supersecret123"),
                    "is_active": True,
                    "is_system_admin": False,
                },
            ],
        )
        connection.execute(
            insert(Workspace),
            [{"id": workspace_id, "name": "Workspace Concorrencia", "description": None}],
        )
        connection.execute(
            insert(WorkspaceMember),
            [
                {
                    "id": uuid.uuid4(),
                    "workspace_id": workspace_id,
                    "user_id": owner_id,
                    "role": WorkspaceRole.OWNER,
                },
                {
                    "id": uuid.uuid4(),
                    "workspace_id": workspace_id,
                    "user_id": candidate_id,
                    "role": WorkspaceRole.MEMBER,
                },
            ],
        )
    engine.dispose()
    return workspace_id, owner_id, candidate_id


def test_get_owner_for_update_serializes_concurrent_access(db_session):
    """Duas conexões independentes tentam travar a linha do Owner do mesmo
    workspace; a segunda MUST bloquear até a primeira liberar (commit ou
    rollback) — nunca as duas obtêm o lock ao mesmo tempo (research.md #20)."""
    workspace_id, _owner_id, _candidate_id = _setup_committed_workspace_with_owner()

    engine_a = create_engine(settings.DATABASE_URL)
    engine_b = create_engine(settings.DATABASE_URL)
    session_a: Session = sessionmaker(bind=engine_a)()
    session_b: Session = sessionmaker(bind=engine_b)()

    events: list[str] = []
    a_acquired = threading.Event()
    b_acquired = threading.Event()

    def _hold_lock_in_a() -> None:
        WorkspaceMemberRepository(session_a).get_owner_for_update(workspace_id)
        events.append("a_acquired")
        a_acquired.set()
        time.sleep(0.5)  # segura o lock propositalmente
        session_a.rollback()  # libera o lock sem persistir nada
        events.append("a_released")

    def _try_lock_in_b() -> None:
        WorkspaceMemberRepository(session_b).get_owner_for_update(workspace_id)
        b_acquired.set()
        events.append("b_acquired")
        session_b.rollback()

    thread_a = threading.Thread(target=_hold_lock_in_a)
    thread_b = threading.Thread(target=_try_lock_in_b)

    try:
        thread_a.start()
        # Sincroniza no evento real (não num sleep "no escuro"): só inicia B
        # depois que A confirmadamente já obteve o lock, eliminando a corrida
        # entre "A pediu o lock" e "B também pede" que tornava este teste
        # instável sob variação de latência/agendamento de threads.
        assert a_acquired.wait(timeout=5), "A deveria ter obtido o lock"
        thread_b.start()

        # Enquanto A ainda segura o lock, B não pode ter conseguido o dele.
        still_blocked = not b_acquired.wait(timeout=0.2)
        assert still_blocked, "B não deveria conseguir o lock enquanto A o mantém"

        thread_a.join(timeout=5)
        thread_b.join(timeout=5)
    finally:
        session_a.close()
        session_b.close()
        engine_a.dispose()
        engine_b.dispose()

    # "a_released" e "b_acquired" são disparados por lados opostos do MESMO
    # evento no Postgres (o rollback de A libera a linha e desbloqueia B no
    # mesmo instante) — a ordem entre esses dois, no nível de log em Python,
    # é uma corrida de agendamento de threads sem significado (ambos ocorrem
    # a frações de milissegundo um do outro) e não deve ser exigida. O que
    # importa — B nunca adquire o lock ENQUANTO A o mantém — já foi validado
    # acima por `still_blocked`; aqui só confirmamos que os três eventos
    # esperados ocorreram, nesta ordem mínima.
    assert events[0] == "a_acquired"
    assert set(events) == {"a_acquired", "a_released", "b_acquired"}


def test_concurrent_transfer_ownership_only_one_succeeds(db_session):
    """Duas "instâncias" tentam transferir a titularidade do mesmo workspace
    ao mesmo tempo; graças ao duplo `SELECT ... FOR UPDATE` + reconfirmação
    sob lock (research.md #20), exatamente uma persiste, a outra encontra o
    Owner já alterado e é rejeitada — nunca duas, nunca zero Owners."""
    workspace_id, owner_id, candidate_id = _setup_committed_workspace_with_owner()

    engine_a = create_engine(settings.DATABASE_URL)
    engine_b = create_engine(settings.DATABASE_URL)
    session_a: Session = sessionmaker(bind=engine_a)()
    session_b: Session = sessionmaker(bind=engine_b)()

    results: dict[str, str] = {}

    def _attempt_transfer(session: Session, key: str) -> None:
        service = WorkspaceMemberService(
            WorkspaceMemberRepository(session),
            WorkspaceRepository(session),
            UserRepository(session),
            TaskRepository(session),
        )
        try:
            service.transfer_ownership(workspace_id, owner_id, candidate_id)
            results[key] = "success"
        except Exception as exc:  # noqa: BLE001 — captura ambos os desfechos possíveis
            results[key] = type(exc).__name__

    thread_a = threading.Thread(target=_attempt_transfer, args=(session_a, "a"))
    thread_b = threading.Thread(target=_attempt_transfer, args=(session_b, "b"))

    try:
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)
    finally:
        session_a.close()
        session_b.close()
        engine_a.dispose()
        engine_b.dispose()

    outcomes = list(results.values())
    assert outcomes.count("success") == 1
    assert outcomes.count("ConflictError") == 1

    # Estado final: exatamente um OWNER no workspace, nunca zero nem dois.
    owners = db_session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.role == WorkspaceRole.OWNER
        )
    ).scalars().all()
    assert len(owners) == 1
