"""T086 [US7] — validação isolada de `UserRepository.update`/`email_taken`,
antes de Service/Routes existirem: persistência crua, sem regra de negócio
(Constitution III)."""

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
