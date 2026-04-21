"""
Extended tests for SerialWorker — covers missing lines for full coverage.

Targets:
  - Line 41:  is_connected property
  - Lines 97-98: General Exception in reading loop
  - Lines 113-114: _close when serial is None or not open
  - Line 168: SerialManager.connect_serial when thread already running
  - Line 182: SerialManager.cleanup
"""

from unittest.mock import MagicMock, patch, PropertyMock

import serial
import pytest
from PySide6.QtWidgets import QApplication

from app.core.serial_worker import SerialWorker, SerialManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def worker(qapp):
    return SerialWorker()


# ── is_connected property (line 41) ──────────────────────────────────

class TestIsConnected:

    def test_is_connected_false_when_no_serial(self, worker):
        """_serial is None → is_connected must be False."""
        assert worker._serial is None
        assert worker.is_connected is False

    def test_is_connected_true_when_serial_open(self, worker):
        """Mock serial with is_open=True → is_connected must be True."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        worker._serial = mock_serial
        assert worker.is_connected is True

    def test_is_connected_false_when_serial_closed(self, worker):
        """Mock serial with is_open=False → is_connected must be False."""
        mock_serial = MagicMock()
        mock_serial.is_open = False
        worker._serial = mock_serial
        assert worker.is_connected is False


# ── set_baudrate ──────────────────────────────────────────────────────

class TestSetBaudrate:

    def test_set_baudrate(self, worker):
        """set_baudrate must update the internal _baudrate."""
        worker.set_baudrate(9600)
        assert worker._baudrate == 9600


# ── _close edge cases (lines 108-117) ────────────────────────────────

class TestCloseEdgeCases:

    def test_close_when_serial_none(self, worker):
        """_close with _serial=None should not raise and must emit False."""
        worker._serial = None
        mock_conn = MagicMock()
        worker.connection_changed.connect(mock_conn)

        worker._close()

        assert worker._serial is None
        mock_conn.assert_called_once_with(False)

    def test_close_when_serial_not_open(self, worker):
        """_serial exists but is_open=False → skip close(), set _serial=None."""
        mock_serial = MagicMock()
        mock_serial.is_open = False
        worker._serial = mock_serial

        mock_conn = MagicMock()
        worker.connection_changed.connect(mock_conn)

        worker._close()

        mock_serial.close.assert_not_called()
        assert worker._serial is None
        mock_conn.assert_called_once_with(False)

    def test_close_when_serial_close_raises(self, worker):
        """_serial.close() raises → exception caught, _serial set to None."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.close.side_effect = OSError("port vanished")
        worker._serial = mock_serial

        mock_conn = MagicMock()
        worker.connection_changed.connect(mock_conn)

        worker._close()

        mock_serial.close.assert_called_once()
        assert worker._serial is None
        mock_conn.assert_called_once_with(False)


# ── General exception in the read loop (lines 97-98) ─────────────────

class TestReadLoopGeneralException:

    @patch("app.core.serial_worker.serial.Serial")
    def test_general_exception_in_read_loop(self, mock_serial_class, worker):
        """A non-SerialException during readline should be caught and
        the loop should continue (not crash or set _running=False)."""
        mock_ser = MagicMock()
        mock_serial_class.return_value = mock_ser

        type(mock_ser).in_waiting = PropertyMock(return_value=1)

        call_count = 0

        def readline_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("unexpected failure")
            # On second call, stop the loop gracefully
            worker.stop_reading()
            return b"READY\r\n"

        mock_ser.readline.side_effect = readline_effect

        mock_err = MagicMock()
        worker.error_occurred.connect(mock_err)

        worker.set_port("COM3")
        worker.start_reading()

        # The RuntimeError must NOT have triggered error_occurred
        # (that signal is only for SerialException).
        mock_err.assert_not_called()
        # Loop kept running and processed the second call
        assert call_count == 2


# ── Parsing boundary / incomplete values ──────────────────────────────

class TestParseBoundary:

    def test_parse_button_boundary_values(self, worker):
        """B:2,4,1 should emit button_event(2, 4, True)."""
        mock_btn = MagicMock()
        worker.button_event.connect(mock_btn)

        worker._parse_line("B:2,4,1")
        mock_btn.assert_called_once_with(2, 4, True)

    def test_parse_pot_boundary_min(self, worker):
        """P:0,0 should emit pot_event(0, 0)."""
        mock_pot = MagicMock()
        worker.pot_event.connect(mock_pot)

        worker._parse_line("P:0,0")
        mock_pot.assert_called_once_with(0, 0)

    def test_parse_pot_boundary_max(self, worker):
        """P:2,1023 should emit pot_event(2, 1023)."""
        mock_pot = MagicMock()
        worker.pot_event.connect(mock_pot)

        worker._parse_line("P:2,1023")
        mock_pot.assert_called_once_with(2, 1023)

    def test_parse_button_incomplete(self, worker):
        """B:1,2 (missing third field) should not emit button_event."""
        mock_btn = MagicMock()
        worker.button_event.connect(mock_btn)

        worker._parse_line("B:1,2")
        mock_btn.assert_not_called()

    def test_parse_pot_incomplete(self, worker):
        """P:0 (missing value) should not emit pot_event."""
        mock_pot = MagicMock()
        worker.pot_event.connect(mock_pot)

        worker._parse_line("P:0")
        mock_pot.assert_not_called()


# ── SerialManager (lines 168, 182) ───────────────────────────────────

class TestSerialManagerExtended:

    @patch("PySide6.QtCore.QThread.start")
    @patch("PySide6.QtCore.QThread.quit")
    @patch("PySide6.QtCore.QThread.wait")
    @patch("PySide6.QtCore.QThread.isRunning", return_value=True)
    def test_manager_connect_when_already_running(
        self, mock_is_running, mock_wait, mock_quit, mock_start
    ):
        """If thread is already running, disconnect_serial must be
        called before starting a new connection."""
        manager = SerialManager()

        manager.connect_serial("COM5", 115200)

        # disconnect_serial was triggered because isRunning() returned True
        mock_quit.assert_called_once()
        mock_wait.assert_called_once_with(3000)

        # Then the new connection was started
        assert manager.worker._port == "COM5"
        mock_start.assert_called_once()

    @patch("PySide6.QtCore.QThread.start")
    @patch("PySide6.QtCore.QThread.quit")
    @patch("PySide6.QtCore.QThread.wait")
    def test_manager_cleanup(self, mock_wait, mock_quit, mock_start):
        """cleanup() must delegate to disconnect_serial."""
        manager = SerialManager()

        manager.cleanup()

        assert not manager.worker._running
        mock_quit.assert_called_once()
        mock_wait.assert_called_once_with(3000)
