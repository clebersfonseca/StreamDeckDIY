"""
Testes para o módulo updater — parsing de versão, check e download.
"""

import io
import shutil
from unittest.mock import MagicMock, patch

import pytest
import requests
from PySide6.QtWidgets import QApplication

from app.core.updater import (
    _parse_version,
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_API_URL,
    _CheckWorker,
    _DownloadWorker,
    UpdateChecker,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ══════════════════════════════════════════════════════════════
#  Testes Originais (Parsing e Config)
# ══════════════════════════════════════════════════════════════


class TestParseVersion:
    """Testes para a função _parse_version."""

    def test_basic_version(self):
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_without_v_prefix(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_uppercase_v(self):
        assert _parse_version("V1.2.3") == (1, 2, 3)

    def test_zero_version(self):
        assert _parse_version("v0.0.0") == (0, 0, 0)

    def test_large_numbers(self):
        assert _parse_version("v10.20.300") == (10, 20, 300)

    def test_two_parts(self):
        assert _parse_version("v1.2") == (1, 2)

    def test_single_part(self):
        assert _parse_version("v5") == (5,)

    def test_invalid_parts_become_zero(self):
        assert _parse_version("v1.abc.3") == (1, 0, 3)

    def test_with_whitespace(self):
        assert _parse_version("  v1.2.3  ") == (1, 2, 3)

    def test_empty_string(self):
        result = _parse_version("")
        assert result == (0,)


class TestVersionComparison:
    """Testes para comparação de versões usando tuplas."""

    def test_newer_patch(self):
        assert _parse_version("v0.1.1") > _parse_version("v0.1.0")

    def test_newer_minor(self):
        assert _parse_version("v0.2.0") > _parse_version("v0.1.9")

    def test_newer_major(self):
        assert _parse_version("v1.0.0") > _parse_version("v0.99.99")

    def test_same_version(self):
        assert not (_parse_version("v1.0.0") > _parse_version("v1.0.0"))

    def test_older_version(self):
        assert not (_parse_version("v0.1.0") > _parse_version("v0.2.0"))

    def test_equality(self):
        assert _parse_version("v1.2.3") == _parse_version("1.2.3")


class TestGitHubConfig:
    """Testes para a configuração do GitHub."""

    def test_owner(self):
        assert GITHUB_OWNER == "clebersfonseca"

    def test_repo(self):
        assert GITHUB_REPO == "StreamDeckDIY"

    def test_api_url_format(self):
        assert GITHUB_API_URL.startswith("https://api.github.com/repos/")
        assert GITHUB_OWNER in GITHUB_API_URL
        assert GITHUB_REPO in GITHUB_API_URL
        assert GITHUB_API_URL.endswith("/releases/latest")


# ══════════════════════════════════════════════════════════════
#  Novos Testes (Workers com Mocks)
# ══════════════════════════════════════════════════════════════


class TestCheckWorker:
    """Testes para consulta da API do GitHub."""

    @patch("app.core.updater.requests.get")
    @patch("app.core.updater.__version__", "0.0.1")
    def test_run_has_update(self, mock_get, qapp):
        # Simula resposta da API indicando versão mais nova
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v0.0.2",
            "body": "Changelog",
            "zipball_url": "http://zip",
            "html_url": "http://html",
            "published_at": "date"
        }
        mock_get.return_value = mock_resp
        
        worker = _CheckWorker()
        mock_slot = MagicMock()
        worker.finished.connect(mock_slot)
        
        worker.run()
        
        mock_slot.assert_called_once()
        result = mock_slot.call_args[0][0]
        assert result["has_update"] is True
        assert result["remote_tag"] == "v0.0.2"

    @patch("app.core.updater.requests.get")
    @patch("app.core.updater.__version__", "1.0.0")
    def test_run_up_to_date(self, mock_get, qapp):
        # Simula resposta com versão igual ou mais antiga
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v1.0.0"}
        mock_get.return_value = mock_resp
        
        worker = _CheckWorker()
        mock_slot = MagicMock()
        worker.finished.connect(mock_slot)
        
        worker.run()
        
        mock_slot.assert_called_once()
        result = mock_slot.call_args[0][0]
        assert result["has_update"] is False
        assert result["reason"] == "up_to_date"

    @patch("app.core.updater.requests.get")
    def test_run_no_release_yet(self, mock_get, qapp):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        
        worker = _CheckWorker()
        mock_slot = MagicMock()
        worker.finished.connect(mock_slot)
        
        worker.run()
        
        mock_slot.assert_called_once()
        result = mock_slot.call_args[0][0]
        assert result["has_update"] is False
        assert result["reason"] == "no_release"

    @patch("app.core.updater.requests.get")
    def test_run_connection_error(self, mock_get, qapp):
        mock_get.side_effect = requests.ConnectionError("Sem net")
        
        worker = _CheckWorker()
        mock_err = MagicMock()
        worker.error.connect(mock_err)
        
        worker.run()
        
        mock_err.assert_called_once()
        assert "Sem conexão" in mock_err.call_args[0][0]


class TestDownloadWorker:
    """Testes para o fluxo de download e extração."""

    @patch("app.core.updater.shutil.rmtree")
    @patch("app.core.updater.zipfile.ZipFile")
    @patch("app.core.updater.requests.get")
    @patch("app.core.updater._project_root")
    def test_run_success(self, mock_root, mock_get, mock_zip, mock_rmtree, qapp, tmp_path):
        """Simula um download com sucesso e extração (sem IO real de zip)."""
        mock_root.return_value = tmp_path
        
        # Simular response do requests.get(stream=True)
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value = mock_resp
        
        worker = _DownloadWorker("http://fake.url/zip", make_backup=False)
        mock_fin = MagicMock()
        worker.finished.connect(mock_fin)
        mock_prog = MagicMock()
        worker.progress.connect(mock_prog)
        
        # Cria a pasta temporária "extraída" pra não quebrar a lógica do iterdir
        tmp_dir = tmp_path / "_update_tmp" / "extracted"
        tmp_dir.mkdir(parents=True)
        (tmp_dir / "app").mkdir() # Simula conteúdo
        
        worker.run()
        
        mock_fin.assert_called_once_with(True, "Atualização instalada com sucesso!")
        # Progresso deve ter emitido várias vezes, chegando a 100
        mock_prog.assert_any_call(100)

    @patch("app.core.updater._project_root")
    @patch("app.core.updater.requests.get")
    def test_run_connection_error(self, mock_get, mock_root, qapp, tmp_path):
        mock_root.return_value = tmp_path
        mock_get.side_effect = requests.Timeout("Lento")
        
        worker = _DownloadWorker("http://fake.url/zip", make_backup=False)
        mock_fin = MagicMock()
        worker.finished.connect(mock_fin)
        
        worker.run()
        
        mock_fin.assert_called_once_with(False, "Download expirou. Tente novamente.")


class TestUpdateChecker:
    """Testes para os métodos de coordenação de threads do UpdateChecker."""

    @patch("PySide6.QtCore.QThread.start")
    def test_check_spawns_thread(self, mock_start, qapp):
        checker = UpdateChecker()
        checker.check()
        
        mock_start.assert_called_once()

    def test_on_check_finished_emits_correct_signal(self, qapp):
        checker = UpdateChecker()
        
        mock_avail = MagicMock()
        mock_no_update = MagicMock()
        checker.update_available.connect(mock_avail)
        checker.no_update.connect(mock_no_update)
        
        # Com update
        checker._on_check_finished({"has_update": True, "remote_tag": "v2", "current": "v1"})
        mock_avail.assert_called_once()
        mock_no_update.assert_not_called()
        
        mock_avail.reset_mock()
        
        # Sem update
        checker._on_check_finished({"has_update": False, "reason": "up_to_date", "current": "v2"})
        mock_avail.assert_not_called()
        mock_no_update.assert_called_once()

    @patch("app.core.updater.os.execl")
    @patch("app.core.updater.sys.executable", "python3")
    @patch("app.core.updater.os.chdir")
    def test_restart_application(self, mock_chdir, mock_execl):
        UpdateChecker.restart_application()
        mock_execl.assert_called_once_with("python3", "python3", "-m", "app.main")
