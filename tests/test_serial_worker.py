"""
Testes para o SerialWorker usando Mocks.
Verifica o parseamento do protocolo Arduino e o controle da Thread.
"""

from unittest.mock import MagicMock, patch
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


class TestSerialParsing:
    """Testes do interpretador de linhas do protocolo."""

    def test_parse_ready(self, worker):
        mock_slot = MagicMock()
        worker.arduino_ready.connect(mock_slot)
        
        worker._parse_line("READY")
        mock_slot.assert_called_once()

    def test_parse_button_pressed(self, worker):
        mock_slot = MagicMock()
        worker.button_event.connect(mock_slot)
        
        worker._parse_line("B:1,2,1")
        mock_slot.assert_called_once_with(1, 2, True)

    def test_parse_button_released(self, worker):
        mock_slot = MagicMock()
        worker.button_event.connect(mock_slot)
        
        worker._parse_line("B:0,4,0")
        mock_slot.assert_called_once_with(0, 4, False)

    def test_parse_button_invalid(self, worker):
        mock_slot = MagicMock()
        worker.button_event.connect(mock_slot)
        
        worker._parse_line("B:x,y,z")
        mock_slot.assert_not_called()

    def test_parse_pot(self, worker):
        mock_slot = MagicMock()
        worker.pot_event.connect(mock_slot)
        
        worker._parse_line("P:2,512")
        mock_slot.assert_called_once_with(2, 512)

    def test_parse_pot_invalid(self, worker):
        mock_slot = MagicMock()
        worker.pot_event.connect(mock_slot)
        
        worker._parse_line("P:a,b")
        mock_slot.assert_not_called()

    def test_parse_unknown(self, worker):
        # Não deve crashear
        worker._parse_line("TESTE DE LIXO")
        worker._parse_line("")


class TestSerialLoop:
    """Testes do loop de conexão e leitura."""

    def test_start_reading_no_port(self, worker):
        mock_slot = MagicMock()
        worker.error_occurred.connect(mock_slot)
        
        worker.start_reading()
        mock_slot.assert_called_once()
        assert "Nenhuma porta" in mock_slot.call_args[0][0]

    @patch("app.core.serial_worker.serial.Serial")
    def test_start_reading_connection_error(self, mock_serial_class, worker):
        mock_serial_class.side_effect = serial.SerialException("Access denied")
        
        mock_err = MagicMock()
        mock_conn = MagicMock()
        worker.error_occurred.connect(mock_err)
        worker.connection_changed.connect(mock_conn)
        
        worker.set_port("COM3")
        worker.start_reading()
        
        mock_err.assert_called_once()
        mock_conn.assert_called_once_with(False)

    @patch("app.core.serial_worker.serial.Serial")
    def test_start_reading_loop(self, mock_serial_class, worker):
        """Simula a abertura e uma leitura antes de parar."""
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance
        
        # Simular que há dados
        mock_serial_instance.in_waiting = 1
        
        # Simular a leitura de um botão, e então parar o loop
        def mock_readline():
            worker.stop_reading()  # Para a thread no próximo ciclo
            return b"B:0,0,1\r\n"
            
        mock_serial_instance.readline.side_effect = mock_readline
        
        mock_btn = MagicMock()
        worker.button_event.connect(mock_btn)
        mock_conn = MagicMock()
        worker.connection_changed.connect(mock_conn)
        
        worker.set_port("COM3")
        worker.start_reading()  # Fica em loop até stop_reading ser chamado
        
        mock_btn.assert_called_once_with(0, 0, True)
        
        # Deve ter emitido True (ao conectar) e False (ao desconectar no finally/close)
        assert mock_conn.call_count == 2
        mock_conn.assert_any_call(True)
        mock_conn.assert_any_call(False)

    @patch("app.core.serial_worker.serial.Serial")
    def test_read_exception_breaks_loop(self, mock_serial_class, worker):
        """Simula uma falha de leitura (cabo desconectado)."""
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance
        
        # type property (property mock) requires PropertyMock, but we can just override the attribute directly
        type(mock_serial_instance).in_waiting = 1
        
        mock_serial_instance.readline.side_effect = serial.SerialException("Device removed")
        
        mock_err = MagicMock()
        worker.error_occurred.connect(mock_err)
        
        worker.set_port("COM3")
        worker.start_reading()
        
        mock_err.assert_called_once()
        assert "perdida" in mock_err.call_args[0][0]
        assert not worker._running


class TestSerialManager:
    """Testes do wrapper da thread."""

    @patch("PySide6.QtCore.QThread.start")
    @patch("PySide6.QtCore.QThread.quit")
    @patch("PySide6.QtCore.QThread.wait")
    def test_manager_lifecycle(self, mock_wait, mock_quit, mock_start):
        manager = SerialManager()
        
        # Testa a lógica de connect/disconnect
        manager.connect_serial("COM4", 9600)
        assert manager.worker._port == "COM4"
        assert manager.worker._baudrate == 9600
        
        mock_start.assert_called_once()
        
        manager.disconnect_serial()
        assert not manager.worker._running
        mock_quit.assert_called_once()
        mock_wait.assert_called_once()

    @patch("app.core.serial_worker.serial.tools.list_ports.comports")
    def test_list_ports(self, mock_comports):
        # Cria um mock que imita um objeto comport
        port1 = MagicMock()
        port1.device = "COM1"
        port1.description = "Porta 1"
        port1.hwid = "123"
        
        mock_comports.return_value = [port1]
        
        ports = SerialWorker.list_ports()
        assert len(ports) == 1
        assert ports[0]["device"] == "COM1"
        assert ports[0]["description"] == "Porta 1"
