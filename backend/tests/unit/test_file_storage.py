"""T097 [US10] — testes unitários de `app/utils/file_storage.py`: validação
de tipo/tamanho, geração de nome de armazenamento (prevenção de path
traversal, research.md #12), gravação/remoção física em disco. Isolado do
disco real via `tmp_path` (nunca toca `ATTACHMENTS_DIR` de dev/CI)."""

import uuid

import pytest

from app.core.config import settings
from app.utils import file_storage


@pytest.fixture(autouse=True)
def _isolated_attachments_dir(tmp_path, monkeypatch):
    """Garante que nenhum teste desta suíte grava fora de um diretório
    temporário descartável do pytest."""
    monkeypatch.setattr(settings, "ATTACHMENTS_DIR", str(tmp_path))
    return tmp_path


# --- is_content_type_allowed ----------------------------------------------


def test_is_content_type_allowed_for_configured_type() -> None:
    assert file_storage.is_content_type_allowed("application/pdf") is True


def test_is_content_type_allowed_rejects_unlisted_type() -> None:
    assert file_storage.is_content_type_allowed("application/x-msdownload") is False


# --- is_size_allowed -------------------------------------------------------


def test_is_size_allowed_within_limit() -> None:
    assert file_storage.is_size_allowed(1024) is True


def test_is_size_allowed_at_exact_limit() -> None:
    assert file_storage.is_size_allowed(settings.ATTACHMENTS_MAX_SIZE_BYTES) is True


def test_is_size_allowed_rejects_above_limit() -> None:
    assert file_storage.is_size_allowed(settings.ATTACHMENTS_MAX_SIZE_BYTES + 1) is False


# --- generate_storage_filename ---------------------------------------------


def test_generate_storage_filename_preserves_safe_extension() -> None:
    filename = file_storage.generate_storage_filename("relatorio.pdf")

    assert filename.endswith(".pdf")
    uuid.UUID(filename.removesuffix(".pdf"))  # prefixo é sempre um UUID válido


def test_generate_storage_filename_ignores_directory_components() -> None:
    """Prevenção de path traversal (research.md #12): mesmo que o nome
    original contenha `../` ou separadores de diretório, o nome de
    armazenamento gerado nunca reflete isso — só a extensão é aproveitada."""
    filename = file_storage.generate_storage_filename("../../etc/passwd.pdf")

    assert "/" not in filename
    assert "\\" not in filename
    assert ".." not in filename
    assert filename.endswith(".pdf")


def test_generate_storage_filename_sanitizes_unsafe_extension() -> None:
    filename = file_storage.generate_storage_filename("script.php;.jpg")

    assert ";" not in filename
    assert "/" not in filename


def test_generate_storage_filename_handles_no_extension() -> None:
    filename = file_storage.generate_storage_filename("semextensao")

    uuid.UUID(filename)  # nome é só o UUID, sem sufixo


def test_generate_storage_filename_always_unique() -> None:
    first = file_storage.generate_storage_filename("mesmo-nome.pdf")
    second = file_storage.generate_storage_filename("mesmo-nome.pdf")

    assert first != second


# --- save_file / delete_file ----------------------------------------------


def test_save_file_writes_bytes_to_attachments_dir(tmp_path) -> None:
    storage_filename = file_storage.generate_storage_filename("documento.pdf")

    storage_path = file_storage.save_file(b"conteudo binario", storage_filename)

    written_file = tmp_path / storage_path
    assert written_file.exists()
    assert written_file.read_bytes() == b"conteudo binario"


def test_save_file_creates_attachments_dir_when_missing(tmp_path) -> None:
    nested_dir = tmp_path / "nested" / "uploads"
    from app.core.config import settings as _settings

    _settings.ATTACHMENTS_DIR = str(nested_dir)

    storage_filename = file_storage.generate_storage_filename("arquivo.txt")
    file_storage.save_file(b"dados", storage_filename)

    assert (nested_dir / storage_filename).exists()


def test_delete_file_removes_existing_file(tmp_path) -> None:
    storage_filename = file_storage.generate_storage_filename("apagar.txt")
    file_storage.save_file(b"dados", storage_filename)
    assert (tmp_path / storage_filename).exists()

    file_storage.delete_file(storage_filename)

    assert not (tmp_path / storage_filename).exists()


def test_delete_file_is_noop_when_file_missing() -> None:
    # Não deve levantar exceção — quem trata reconciliação/log é o Service.
    file_storage.delete_file("inexistente.pdf")


def test_resolve_storage_path_joins_with_attachments_dir(tmp_path) -> None:
    resolved = file_storage.resolve_storage_path("arquivo.pdf")

    assert resolved == tmp_path / "arquivo.pdf"
