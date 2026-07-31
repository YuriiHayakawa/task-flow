"""T086 [US7] — validação isolada de `UserRepository.update`/`email_taken`,
antes de Service/Routes existirem: persistência crua, sem regra de negócio
(Constitution III).

T113 [US13] — estende com `list_all` (paginação real + filtro `is_active`)."""

from app.repositories.user_repository import UserRepository


def test_email_taken_false_when_unused(db_session, make_user):
    user = make_user()
    repo = UserRepository(db_session)

    assert repo.email_taken("unused@example.com", exclude_user_id=user.id) is False


def test_email_taken_true_when_used_by_another_user(db_session, make_user):
    user = make_user()
    other = make_user(email="taken@example.com")
    repo = UserRepository(db_session)

    assert repo.email_taken("taken@example.com", exclude_user_id=user.id) is True


def test_email_taken_false_when_email_belongs_to_self(db_session, make_user):
    """Sem excluir o próprio usuário, ninguém conseguiria reenviar seu
    próprio e-mail inalterado ao atualizar só o nome."""
    user = make_user(email="mine@example.com")
    repo = UserRepository(db_session)

    assert repo.email_taken("mine@example.com", exclude_user_id=user.id) is False


def test_email_taken_case_insensitive(db_session, make_user):
    user = make_user()
    make_user(email="mixedcase@example.com")
    repo = UserRepository(db_session)

    assert repo.email_taken("MixedCase@Example.com", exclude_user_id=user.id) is True


def test_update_flushes_not_commits(db_session, make_user):
    user = make_user(name="Nome Original")
    repo = UserRepository(db_session)

    user.name = "Nome Alterado"
    updated = repo.update(user)

    assert updated.name == "Nome Alterado"
    # ainda dentro da mesma transação (flush), visível a uma nova consulta:
    reloaded = repo.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.name == "Nome Alterado"


# --- list_all (T113/US13) -------------------------------------------------------
#
# Nota: `list_all` reflete TODA a tabela `users`, sem escopo por workspace —
# alguns testes de concorrência de outras suítes (ex.: test_workspace_
# ownership.py, test_due_soon_scheduler.py) commitam usuários reais numa
# conexão própria (fora da transação isolada de `db_session`), que
# permanecem visíveis até o `alembic downgrade` no fim de toda a sessão de
# testes. Por isso, os testes abaixo nunca assumem que a tabela está vazia
# ou contém só os usuários criados aqui — usam deltas (antes/depois) e
# filtragem por membership, não contagens absolutas.


def test_list_all_returns_all_when_no_filter(db_session, make_user):
    repo = UserRepository(db_session)
    _, total_before = repo.list_all(is_active=None, page=1, page_size=1)
    user_a = make_user(email="list-all-a@example.com")
    user_b = make_user(email="list-all-b@example.com")

    items, total = repo.list_all(is_active=None, page=1, page_size=10_000)

    assert total == total_before + 2
    assert {user_a.id, user_b.id} <= {u.id for u in items}


def test_list_all_filters_by_is_active_true(db_session, make_user):
    active_user = make_user(email="list-active@example.com", is_active=True)
    inactive_user = make_user(email="list-inactive@example.com", is_active=False)
    repo = UserRepository(db_session)

    items, _ = repo.list_all(is_active=True, page=1, page_size=10_000)

    item_ids = {u.id for u in items}
    assert active_user.id in item_ids
    assert inactive_user.id not in item_ids
    assert all(u.is_active for u in items)


def test_list_all_filters_by_is_active_false(db_session, make_user):
    active_user = make_user(email="list-active-2@example.com", is_active=True)
    inactive_user = make_user(email="list-inactive-2@example.com", is_active=False)
    repo = UserRepository(db_session)

    items, _ = repo.list_all(is_active=False, page=1, page_size=10_000)

    item_ids = {u.id for u in items}
    assert inactive_user.id in item_ids
    assert active_user.id not in item_ids
    assert all(not u.is_active for u in items)


def test_list_all_paginates_with_limit_and_offset(db_session, make_user):
    for i in range(5):
        make_user(email=f"list-page-{i}@example.com")
    repo = UserRepository(db_session)

    first_page, total = repo.list_all(is_active=None, page=1, page_size=2)
    second_page, total_again = repo.list_all(is_active=None, page=2, page_size=2)

    assert total >= 5
    assert total_again == total
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {u.id for u in first_page}.isdisjoint({u.id for u in second_page})


def test_list_all_ordered_by_created_at_ascending(db_session, make_user):
    from datetime import timedelta

    user_a = make_user(email="list-order-a@example.com")
    user_b = make_user(email="list-order-b@example.com")
    user_a.created_at = user_b.created_at - timedelta(minutes=5)
    db_session.flush()
    repo = UserRepository(db_session)

    items, _ = repo.list_all(is_active=None, page=1, page_size=10_000)

    relevant_order = [u.id for u in items if u.id in {user_a.id, user_b.id}]
    assert relevant_order == [user_a.id, user_b.id]


def test_list_all_returns_empty_items_for_page_beyond_total(db_session, make_user):
    make_user(email="list-beyond-page@example.com")
    repo = UserRepository(db_session)
    _, total = repo.list_all(is_active=None, page=1, page_size=1)

    items, total_again = repo.list_all(is_active=None, page=total + 100, page_size=1)

    assert items == []
    assert total_again == total
