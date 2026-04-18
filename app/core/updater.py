"""
UpdateChecker — Sistema de atualização automática via GitHub Releases.

Verifica se há uma nova versão disponível no repositório GitHub,
baixa e instala automaticamente com opção de backup.
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QThread, Signal

from app import __version__

logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────
GITHUB_OWNER = "clebersfonseca"
GITHUB_REPO = "StreamDeckDIY"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = 15  # segundos


def _parse_version(tag: str) -> tuple[int, ...]:
    """Converte tag 'v1.2.3' em tupla (1, 2, 3) para comparação."""
    clean = tag.strip().lstrip("vV")
    parts = []
    for part in clean.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _project_root() -> Path:
    """Retorna o diretório raiz do projeto (pai de app/)."""
    return Path(__file__).resolve().parent.parent.parent


# ══════════════════════════════════════════════════════════════
#  Worker — roda em QThread separada
# ══════════════════════════════════════════════════════════════


class _CheckWorker(QObject):
    """Worker que consulta a API do GitHub em background."""

    finished = Signal(dict)   # resultado completo
    error = Signal(str)       # mensagem de erro

    def run(self):
        try:
            logger.info("Verificando atualizações em %s", GITHUB_API_URL)
            resp = requests.get(
                GITHUB_API_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code == 404:
                # Nenhuma release publicada ainda
                self.finished.emit({
                    "has_update": False,
                    "reason": "no_release",
                    "current": __version__,
                })
                return

            resp.raise_for_status()
            data = resp.json()

            remote_tag = data.get("tag_name", "")
            remote_ver = _parse_version(remote_tag)
            local_ver = _parse_version(__version__)

            result = {
                "current": __version__,
                "remote_tag": remote_tag,
                "remote_version": ".".join(str(x) for x in remote_ver),
                "changelog": data.get("body", ""),
                "zipball_url": data.get("zipball_url", ""),
                "html_url": data.get("html_url", ""),
                "published_at": data.get("published_at", ""),
            }

            if remote_ver > local_ver:
                result["has_update"] = True
                result["reason"] = "update_available"
            else:
                result["has_update"] = False
                result["reason"] = "up_to_date"

            self.finished.emit(result)

        except requests.ConnectionError:
            self.error.emit("Sem conexão com a internet.")
        except requests.Timeout:
            self.error.emit("Tempo de conexão esgotado.")
        except requests.HTTPError as exc:
            self.error.emit(f"Erro HTTP: {exc.response.status_code}")
        except Exception as exc:
            logger.exception("Erro inesperado ao verificar atualizações")
            self.error.emit(f"Erro inesperado: {exc}")


class _DownloadWorker(QObject):
    """Worker que baixa e instala a atualização."""

    progress = Signal(int)            # 0-100
    finished = Signal(bool, str)      # (sucesso, mensagem)

    def __init__(self, zipball_url: str, make_backup: bool):
        super().__init__()
        self._url = zipball_url
        self._make_backup = make_backup

    def run(self):
        root = _project_root()
        tmp_dir = root / "_update_tmp"

        try:
            # ── 1. Download ──────────────────────────────────
            self.progress.emit(5)
            logger.info("Baixando atualização de %s", self._url)

            resp = requests.get(self._url, stream=True, timeout=60)
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            zip_path = tmp_dir / "update.zip"
            tmp_dir.mkdir(parents=True, exist_ok=True)

            downloaded = 0
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int((downloaded / total) * 50)  # 0-50%
                        self.progress.emit(5 + pct)

            self.progress.emit(55)

            # ── 2. Extrair ───────────────────────────────────
            logger.info("Extraindo atualização...")
            extract_dir = tmp_dir / "extracted"
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            self.progress.emit(65)

            # O GitHub zipball contém uma pasta raiz tipo
            # "owner-repo-commitsha/", precisamos encontrá-la
            subdirs = list(extract_dir.iterdir())
            if len(subdirs) == 1 and subdirs[0].is_dir():
                source_root = subdirs[0]
            else:
                source_root = extract_dir

            # ── 3. Backup (opcional) ─────────────────────────
            if self._make_backup:
                logger.info("Criando backup...")
                backup_dir = root / "_backup"
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                backup_dir.mkdir(parents=True, exist_ok=True)

                for folder in ("app", "arduino"):
                    src = root / folder
                    if src.exists():
                        shutil.copytree(src, backup_dir / folder)

                # Backup de arquivos soltos importantes
                for fname in ("requirements.txt", "README.md"):
                    src = root / fname
                    if src.exists():
                        shutil.copy2(src, backup_dir / fname)

                logger.info("Backup salvo em %s", backup_dir)

            self.progress.emit(80)

            # ── 4. Copiar novos arquivos ─────────────────────
            logger.info("Instalando nova versão...")
            for folder in ("app", "arduino"):
                new_folder = source_root / folder
                if new_folder.exists():
                    dest = root / folder
                    # Remove __pycache__ do destino
                    for cache in dest.rglob("__pycache__"):
                        shutil.rmtree(cache, ignore_errors=True)
                    # Copia arquivos novos por cima
                    shutil.copytree(
                        new_folder, dest,
                        dirs_exist_ok=True,
                    )

            # Arquivos soltos
            for fname in ("requirements.txt", "README.md"):
                new_file = source_root / fname
                if new_file.exists():
                    shutil.copy2(new_file, root / fname)

            self.progress.emit(95)

            # ── 5. Limpeza ───────────────────────────────────
            shutil.rmtree(tmp_dir, ignore_errors=True)

            self.progress.emit(100)
            logger.info("Atualização instalada com sucesso!")
            self.finished.emit(True, "Atualização instalada com sucesso!")

        except requests.ConnectionError:
            self.finished.emit(False, "Sem conexão com a internet.")
        except requests.Timeout:
            self.finished.emit(False, "Download expirou. Tente novamente.")
        except zipfile.BadZipFile:
            self.finished.emit(False, "Arquivo baixado está corrompido.")
        except Exception as exc:
            logger.exception("Erro ao instalar atualização")
            self.finished.emit(False, f"Erro: {exc}")
        finally:
            # Garante limpeza mesmo em caso de erro
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
#  Classe principal — gerencia os workers
# ══════════════════════════════════════════════════════════════


class UpdateChecker(QObject):
    """
    Gerenciador de atualizações do StreamDeck DIY.

    Signals:
        update_available(dict)  — info da nova versão
        no_update(str)          — mensagem quando está atualizado
        check_error(str)        — erro na verificação
        download_progress(int)  — progresso do download (0-100)
        update_finished(bool, str) — resultado da instalação
    """

    update_available = Signal(dict)
    no_update = Signal(str)
    check_error = Signal(str)
    download_progress = Signal(int)
    update_finished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_thread: QThread | None = None
        self._download_thread: QThread | None = None

    # ── Verificar ────────────────────────────────────────────

    def check(self):
        """Inicia verificação de atualizações em background."""
        if self._check_thread and self._check_thread.isRunning():
            logger.warning("Verificação já em andamento.")
            return

        self._check_thread = QThread()
        self._check_worker = _CheckWorker()
        self._check_worker.moveToThread(self._check_thread)

        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.finished.connect(self._on_check_finished)
        self._check_worker.error.connect(self._on_check_error)
        self._check_worker.finished.connect(self._check_thread.quit)
        self._check_worker.error.connect(self._check_thread.quit)

        self._check_thread.start()

    def _on_check_finished(self, result: dict):
        """Processa resultado da verificação."""
        if result.get("has_update"):
            logger.info(
                "Nova versão disponível: %s (atual: %s)",
                result["remote_tag"], result["current"],
            )
            self.update_available.emit(result)
        elif result.get("reason") == "no_release":
            msg = f"Nenhuma release encontrada no GitHub.\nVersão local: v{result['current']}"
            logger.info(msg)
            self.no_update.emit(msg)
        else:
            msg = f"Você já está na versão mais recente (v{result['current']}) ✅"
            logger.info(msg)
            self.no_update.emit(msg)

    def _on_check_error(self, msg: str):
        """Repassa erro da verificação."""
        logger.error("Erro ao verificar atualizações: %s", msg)
        self.check_error.emit(msg)

    # ── Download & Install ───────────────────────────────────

    def download_and_install(self, zipball_url: str, make_backup: bool = True):
        """Inicia download e instalação em background."""
        if self._download_thread and self._download_thread.isRunning():
            logger.warning("Download já em andamento.")
            return

        self._download_thread = QThread()
        self._download_worker = _DownloadWorker(zipball_url, make_backup)
        self._download_worker.moveToThread(self._download_thread)

        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self.download_progress.emit)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.finished.connect(self._download_thread.quit)

        self._download_thread.start()

    def _on_download_finished(self, success: bool, msg: str):
        """Repassa resultado da instalação."""
        self.update_finished.emit(success, msg)

    # ── Reiniciar aplicação ──────────────────────────────────

    @staticmethod
    def restart_application():
        """Reinicia a aplicação Python."""
        logger.info("Reiniciando aplicação...")
        python = sys.executable
        project_root = str(_project_root())
        os.chdir(project_root)
        os.execl(python, python, "-m", "app.main")
