"""
Testes estendidos para app/core/updater.py — cobertura das linhas faltantes.
"""

import zipfile
from unittest.mock import MagicMock, patch

import pytest
import requests
from PySide6.QtWidgets import QApplication

from app.core.updater import _CheckWorker, _DownloadWorker, UpdateChecker


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ══════════════════════════════════════════════════════════════
#  _CheckWorker — exception handlers (lines 105-111)
# ══════════════════════════════════════════════════════════════


class TestCheckWorkerExtended:

    @patch("app.core.updater.requests.get")
    def test_check_worker_timeout(self, mock_get, qapp):
        mock_get.side_effect = requests.Timeout("timeout")

        worker = _CheckWorker()
        mock_err = MagicMock()
        worker.error.connect(mock_err)

        worker.run()

        mock_err.assert_called_once()
        assert "Tempo de conexão esgotado" in mock_err.call_args[0][0]

    @patch("app.core.updater.requests.get")
    def test_check_worker_http_error(self, mock_get, qapp):
        resp = MagicMock()
        resp.status_code = 500
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
        mock_get.return_value = resp

        worker = _CheckWorker()
        mock_err = MagicMock()
        worker.error.connect(mock_err)

        worker.run()

        mock_err.assert_called_once()
        msg = mock_err.call_args[0][0]
        assert "Erro HTTP" in msg
        assert "500" in msg

    @patch("app.core.updater.requests.get")
    def test_check_worker_generic_exception(self, mock_get, qapp):
        mock_get.side_effect = RuntimeError("something broke")

        worker = _CheckWorker()
        mock_err = MagicMock()
        worker.error.connect(mock_err)

        worker.run()

        mock_err.assert_called_once()
        assert "Erro inesperado" in mock_err.call_args[0][0]


# ══════════════════════════════════════════════════════════════
#  _DownloadWorker — backup, extraction, errors (lines 166-229)
# ══════════════════════════════════════════════════════════════


class TestDownloadWorkerExtended:

    @patch("app.core.updater.shutil.rmtree")
    @patch("app.core.updater.shutil.copytree")
    @patch("app.core.updater.shutil.copy2")
    @patch("app.core.updater.zipfile.ZipFile")
    @patch("app.core.updater.requests.get")
    @patch("app.core.updater._project_root")
    def test_download_worker_with_backup(
        self, mock_root, mock_get, mock_zip, mock_copy2,
        mock_copytree, mock_rmtree, qapp, tmp_path,
    ):
        mock_root.return_value = tmp_path

        # Create existing app dir and requirements.txt for backup
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("x")
        (tmp_path / "requirements.txt").write_text("PySide6")

        # Mock HTTP response
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_get.return_value = mock_resp

        # Prepare extracted directory with a single subdirectory (GitHub-style)
        extract_dir = tmp_path / "_update_tmp" / "extracted"
        extract_dir.mkdir(parents=True)
        sub = extract_dir / "owner-repo-abc123"
        sub.mkdir()

        worker = _DownloadWorker("http://fake/zip", make_backup=True)
        mock_fin = MagicMock()
        worker.finished.connect(mock_fin)

        worker.run()

        mock_fin.assert_called_once_with(True, "Atualização instalada com sucesso!")
        # Verify backup dir was created
        backup_dir = tmp_path / "_backup"
        assert backup_dir.exists()

    @patch("app.core.updater._project_root")
    @patch("app.core.updater.requests.get")
    def test_download_worker_bad_zip(self, mock_get, mock_root, qapp, tmp_path):
        mock_root.return_value = tmp_path

        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "50"}
        mock_resp.iter_content.return_value = [b"bad"]
        mock_get.return_value = mock_resp

        # The real ZipFile will fail on the garbage bytes
        worker = _DownloadWorker("http://fake/zip", make_backup=False)
        mock_fin = MagicMock()
        worker.finished.connect(mock_fin)

        worker.run()

        mock_fin.assert_called_once()
        assert mock_fin.call_args[0][0] is False
        assert "corrompido" in mock_fin.call_args[0][1]

    @patch("app.core.updater._project_root")
    @patch("app.core.updater.requests.get")
    def test_download_worker_connection_error(self, mock_get, mock_root, qapp, tmp_path):
        mock_root.return_value = tmp_path
        mock_get.side_effect = requests.ConnectionError("no net")

        worker = _DownloadWorker("http://fake/zip", make_backup=False)
        mock_fin = MagicMock()
        worker.finished.connect(mock_fin)

        worker.run()

        mock_fin.assert_called_once()
        assert mock_fin.call_args[0][0] is False
        assert "Sem conexão" in mock_fin.call_args[0][1]

    @patch("app.core.updater.shutil.rmtree")
    @patch("app.core.updater.shutil.copytree")
    @patch("app.core.updater.shutil.copy2")
    @patch("app.core.updater.zipfile.ZipFile")
    @patch("app.core.updater.requests.get")
    @patch("app.core.updater._project_root")
    def test_download_worker_subdir_extraction(
        self, mock_root, mock_get, mock_zip, mock_copy2,
        mock_copytree, mock_rmtree, qapp, tmp_path,
    ):
        """When zip contains a single subdirectory, source_root should be that subdir."""
        mock_root.return_value = tmp_path

        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"data"]
        mock_get.return_value = mock_resp

        # Create extracted layout: single subdirectory with app/ and requirements.txt
        extract_dir = tmp_path / "_update_tmp" / "extracted"
        extract_dir.mkdir(parents=True)
        sub = extract_dir / "clebersfonseca-StreamDeckDIY-abc1234"
        sub.mkdir()
        (sub / "app").mkdir()
        (sub / "app" / "core").mkdir()
        (sub / "requirements.txt").write_text("PySide6")

        worker = _DownloadWorker("http://fake/zip", make_backup=False)
        mock_fin = MagicMock()
        worker.finished.connect(mock_fin)

        worker.run()

        mock_fin.assert_called_once_with(True, "Atualização instalada com sucesso!")
        # copytree should have been called with the subdirectory's app folder
        mock_copytree.assert_called()
        src_arg = str(mock_copytree.call_args_list[0][0][0])
        assert "clebersfonseca-StreamDeckDIY-abc1234" in src_arg


# ══════════════════════════════════════════════════════════════
#  UpdateChecker — coordination methods (lines 269-327)
# ══════════════════════════════════════════════════════════════


class TestUpdateCheckerExtended:

    def test_checker_check_already_running(self, qapp):
        checker = UpdateChecker()
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True
        checker._check_thread = mock_thread

        # Should return early without creating a new thread
        checker.check()

        # isRunning was consulted and no new thread was started
        mock_thread.isRunning.assert_called_once()
        assert checker._check_thread is mock_thread

    def test_checker_on_check_finished_no_release(self, qapp):
        checker = UpdateChecker()
        mock_no_update = MagicMock()
        checker.no_update.connect(mock_no_update)

        checker._on_check_finished({
            "has_update": False,
            "reason": "no_release",
            "current": "0.1.0",
        })

        mock_no_update.assert_called_once()
        msg = mock_no_update.call_args[0][0]
        assert "Nenhuma release" in msg

    def test_checker_on_check_error(self, qapp):
        checker = UpdateChecker()
        mock_err = MagicMock()
        checker.check_error.connect(mock_err)

        checker._on_check_error("Sem conexão com a internet.")

        mock_err.assert_called_once_with("Sem conexão com a internet.")

    @patch("PySide6.QtCore.QThread.start")
    def test_checker_download_and_install_spawns_thread(self, mock_start, qapp):
        checker = UpdateChecker()
        checker.download_and_install("http://fake/zip", make_backup=True)

        mock_start.assert_called_once()
        assert checker._download_thread is not None

    def test_checker_download_and_install_already_running(self, qapp):
        checker = UpdateChecker()
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True
        checker._download_thread = mock_thread

        checker.download_and_install("http://fake/zip")

        mock_thread.isRunning.assert_called_once()
        # Thread object should not be replaced
        assert checker._download_thread is mock_thread

    def test_checker_on_download_finished(self, qapp):
        checker = UpdateChecker()
        mock_sig = MagicMock()
        checker.update_finished.connect(mock_sig)

        checker._on_download_finished(True, "Atualização instalada com sucesso!")

        mock_sig.assert_called_once_with(True, "Atualização instalada com sucesso!")
