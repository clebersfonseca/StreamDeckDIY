"""
ActionDialog — Diálogo para configurar a ação de um botão ou potenciômetro.

Permite selecionar o tipo de ação, preencher parâmetros,
e definir um label personalizado.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
    QFileDialog, QCheckBox,
)

from app.core.profile_manager import ActionType, ACTION_METADATA
from app.gui.styles import COLORS


class ActionDialog(QDialog):
    """Diálogo para configurar uma ação de botão ou potenciômetro."""

    def __init__(self, title: str, current_action: dict, for_pot: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setModal(True)

        self._for_pot = for_pot
        self._current_action = current_action
        self._param_inputs: dict[str, QLineEdit] = {}

        self._result_action = current_action.get("action", ActionType.NONE.value)
        self._result_params = current_action.get("params", {})
        self._result_label = current_action.get("label", "")
        self._result_inverted = current_action.get("inverted", False)

        self._setup_ui()
        self._load_current()

    def _setup_ui(self):
        """Cria a interface do diálogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ---- Tipo de ação ----
        action_group = QGroupBox("Tipo de Ação")
        action_layout = QFormLayout(action_group)

        self._action_combo = QComboBox()
        self._populate_actions()
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        action_layout.addRow("Ação:", self._action_combo)

        layout.addWidget(action_group)

        # ---- Parâmetros ----
        self._params_group = QGroupBox("Parâmetros")
        self._params_layout = QFormLayout(self._params_group)
        layout.addWidget(self._params_group)

        # ---- Opções do Potenciômetro ----
        if self._for_pot:
            pot_options_group = QGroupBox("Opções do Potenciômetro")
            pot_options_layout = QVBoxLayout(pot_options_group)

            self._inverted_check = QCheckBox(
                "Inverter direção (maior resistência = menor valor)"
            )
            self._inverted_check.setToolTip(
                "Quando ativado, o potenciômetro opera de forma invertida:\n"
                "maior resistência produz menor volume/valor."
            )
            pot_options_layout.addWidget(self._inverted_check)

            layout.addWidget(pot_options_group)

        # ---- Label ----
        label_group = QGroupBox("Exibição")
        label_layout = QFormLayout(label_group)

        self._label_input = QLineEdit()
        self._label_input.setPlaceholderText("Nome exibido no botão (opcional)")
        label_layout.addRow("Label:", self._label_input)

        layout.addWidget(label_group)

        # ---- Botões ----
        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Limpar")
        clear_btn.setProperty("class", "danger")
        clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Salvar")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_actions(self):
        """Popula o combo de ações, agrupado por categoria."""
        self._action_combo.addItem("— Selecione uma ação —", ActionType.NONE.value)

        # Agrupa por categoria
        categories: dict[str, list] = {}
        for action_type, meta in ACTION_METADATA.items():
            if action_type == ActionType.NONE:
                continue
            # Para potenciômetros, mostra apenas ações compatíveis
            if self._for_pot and not meta.get("for_pot", False):
                continue
            # Para botões, mostra apenas ações que não são exclusivas de pot
            if not self._for_pot and meta.get("for_pot", False) and not meta.get("params"):
                continue

            cat = meta["category"]
            categories.setdefault(cat, []).append((action_type, meta))

        for cat_name, actions in categories.items():
            # Separador de categoria (usando item desabilitado)
            self._action_combo.addItem(f"── {cat_name} ──", "__separator__")
            idx = self._action_combo.count() - 1
            self._action_combo.model().item(idx).setEnabled(False)

            for action_type, meta in actions:
                self._action_combo.addItem(f"  {meta['label']}", action_type.value)

    def _load_current(self):
        """Carrega a ação atual no diálogo."""
        action = self._current_action.get("action", ActionType.NONE.value)
        label = self._current_action.get("label", "")
        inverted = self._current_action.get("inverted", False)

        # Encontra e seleciona a ação no combo
        for i in range(self._action_combo.count()):
            if self._action_combo.itemData(i) == action:
                self._action_combo.setCurrentIndex(i)
                break

        self._label_input.setText(label)

        if self._for_pot:
            self._inverted_check.setChecked(inverted)

    def _on_action_changed(self, index: int):
        """Atualiza os campos de parâmetros quando a ação muda."""
        action_value = self._action_combo.currentData()

        # Limpa parâmetros anteriores
        self._param_inputs.clear()
        while self._params_layout.count() > 0:
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if action_value == ActionType.NONE.value or action_value == "__separator__":
            self._params_group.setVisible(False)
            return

        # Busca metadados da ação
        try:
            action_type = ActionType(action_value)
        except ValueError:
            self._params_group.setVisible(False)
            return

        meta = ACTION_METADATA.get(action_type)
        if not meta or not meta.get("params"):
            self._params_group.setVisible(False)
            return

        self._params_group.setVisible(True)

        for param in meta["params"]:
            name = param["name"]
            label = param["label"]
            param_type = param.get("type", "text")

            if param_type == "file":
                row_layout = QHBoxLayout()
                input_field = QLineEdit()
                input_field.setPlaceholderText(label)
                browse_btn = QPushButton("📁")
                browse_btn.setFixedWidth(36)
                browse_btn.clicked.connect(
                    lambda checked, f=input_field: self._browse_file(f)
                )
                row_layout.addWidget(input_field)
                row_layout.addWidget(browse_btn)

                container = QWidget()
                container.setLayout(row_layout)
                self._params_layout.addRow(f"{label}:", container)
            else:
                input_field = QLineEdit()
                input_field.setPlaceholderText(label)
                self._params_layout.addRow(f"{label}:", input_field)

            # Preenche com valor atual se existir
            current_value = self._current_action.get("params", {}).get(name, "")
            if current_value:
                input_field.setText(str(current_value))

            self._param_inputs[name] = input_field

    def _browse_file(self, line_edit: QLineEdit):
        """Abre diálogo para selecionar arquivo."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Programa", "", "Todos (*)"
        )
        if path:
            line_edit.setText(path)

    def _on_clear(self):
        """Limpa a configuração (define como NONE)."""
        self._result_action = ActionType.NONE.value
        self._result_params = {}
        self._result_label = ""
        self._result_inverted = False
        self.accept()

    def _on_save(self):
        """Salva a configuração."""
        self._result_action = self._action_combo.currentData() or ActionType.NONE.value

        if self._result_action == "__separator__":
            self._result_action = ActionType.NONE.value

        self._result_params = {}
        for name, input_field in self._param_inputs.items():
            self._result_params[name] = input_field.text().strip()

        self._result_label = self._label_input.text().strip()

        if self._for_pot:
            self._result_inverted = self._inverted_check.isChecked()

        self.accept()

    def get_result(self) -> dict:
        """Retorna o resultado da configuração."""
        result = {
            "action": self._result_action,
            "params": self._result_params,
            "label": self._result_label,
        }
        if self._for_pot:
            result["inverted"] = self._result_inverted
        return result
