"""
SerialWorker — Thread Qt para comunicação serial com o Arduino.

Lê dados da porta serial, parseia o protocolo e emite sinais Qt
para botões e potenciômetros.

Protocolo esperado do Arduino:
    B:<linha>,<coluna>,<estado>   (estado: 1=pressionado, 0=solto)
    P:<indice>,<valor>            (valor: 0-1023)
    READY                         (Arduino inicializado)
"""

import logging

from PySide6.QtCore import QObject, QThread, Signal, Slot
import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)


class SerialWorker(QObject):
    """Worker que roda em uma QThread para leitura serial."""

    # Sinais emitidos para a thread principal
    button_event = Signal(int, int, bool)   # (linha, coluna, pressionado)
    pot_event = Signal(int, int)            # (índice, valor 0-1023)
    connection_changed = Signal(bool)       # True=conectado, False=desconectado
    arduino_ready = Signal()                # Arduino enviou "READY"
    error_occurred = Signal(str)            # Mensagem de erro

    def __init__(self, parent=None):
        super().__init__(parent)
        self._port = None
        self._baudrate = 115200
        self._serial = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def set_port(self, port: str):
        """Define a porta serial (ex: 'COM3', '/dev/ttyACM0')."""
        self._port = port

    def set_baudrate(self, baudrate: int):
        """Define o baudrate (padrão: 115200)."""
        self._baudrate = baudrate

    @staticmethod
    def list_ports() -> list[dict]:
        """Lista portas seriais disponíveis."""
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append({
                "device": port_info.device,
                "description": port_info.description,
                "hwid": port_info.hwid,
            })
        return ports

    @Slot()
    def start_reading(self):
        """Inicia a conexão e leitura da porta serial."""
        if not self._port:
            self.error_occurred.emit("Nenhuma porta serial selecionada.")
            return

        self._running = True

        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=0.1,  # Timeout curto para permitir parar a thread
            )
            logger.info("Conectado à porta %s @ %d baud", self._port, self._baudrate)
            self.connection_changed.emit(True)
        except serial.SerialException as e:
            logger.error("Erro ao abrir porta serial: %s", e)
            self.error_occurred.emit(f"Erro ao abrir porta serial: {e}")
            self.connection_changed.emit(False)
            return

        # Loop principal de leitura
        while self._running:
            try:
                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        self._parse_line(line)
            except serial.SerialException as e:
                logger.error("Erro na leitura serial: %s", e)
                self.error_occurred.emit(f"Conexão serial perdida: {e}")
                self._running = False
            except Exception as e:
                logger.error("Erro inesperado no worker serial: %s", e)

        # Limpeza ao parar
        self._close()

    @Slot()
    def stop_reading(self):
        """Para a leitura e fecha a conexão serial."""
        self._running = False

    def _close(self):
        """Fecha a conexão serial."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self.connection_changed.emit(False)
        logger.info("Conexão serial fechada.")

    def _parse_line(self, line: str):
        """Parseia uma linha do protocolo serial do Arduino."""
        if line == "READY":
            logger.info("Arduino está pronto.")
            self.arduino_ready.emit()
            return

        if line.startswith("B:"):
            # Formato: B:<linha>,<coluna>,<estado>
            try:
                parts = line[2:].split(",")
                row = int(parts[0])
                col = int(parts[1])
                pressed = parts[2] == "1"
                self.button_event.emit(row, col, pressed)
                logger.debug("Botão [%d,%d] %s", row, col,
                             "pressionado" if pressed else "solto")
            except (ValueError, IndexError) as e:
                logger.warning("Linha de botão inválida: '%s' (%s)", line, e)

        elif line.startswith("P:"):
            # Formato: P:<indice>,<valor>
            try:
                parts = line[2:].split(",")
                index = int(parts[0])
                value = int(parts[1])
                self.pot_event.emit(index, value)
                logger.debug("Pot [%d] = %d", index, value)
            except (ValueError, IndexError) as e:
                logger.warning("Linha de pot inválida: '%s' (%s)", line, e)

        else:
            logger.debug("Linha serial não reconhecida: '%s'", line)


class SerialManager:
    """Gerencia o SerialWorker e sua QThread."""

    def __init__(self):
        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)

        # Conecta start da thread ao início da leitura
        self.thread.started.connect(self.worker.start_reading)

    def connect_serial(self, port: str, baudrate: int = 115200):
        """Inicia a conexão serial em uma thread separada."""
        if self.thread.isRunning():
            self.disconnect_serial()

        self.worker.set_port(port)
        self.worker.set_baudrate(baudrate)
        self.thread.start()

    def disconnect_serial(self):
        """Para a leitura e encerra a thread."""
        self.worker.stop_reading()
        self.thread.quit()
        self.thread.wait(3000)  # Aguarda até 3s para finalizar

    def cleanup(self):
        """Limpeza final ao fechar a aplicação."""
        self.disconnect_serial()
