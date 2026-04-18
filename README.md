# 🎛 StreamDeck DIY

StreamDeck caseiro para controle do **OBS Studio** e **Windows**, construído com **Arduino Pro Micro** e uma aplicação desktop em **Python + PySide6**.

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)
![Arduino](https://img.shields.io/badge/board-Arduino%20Pro%20Micro-teal.svg)

---

## 📋 Sobre o Projeto

Este projeto implementa um Stream Deck DIY completo, composto por duas partes:

1. **Firmware Arduino** — Código para o Arduino Pro Micro que lê uma matriz de botões (3×5) e 3 potenciômetros, enviando os eventos via Serial USB.
2. **Aplicação Desktop** — Software em Python com interface gráfica (PySide6) que recebe os sinais do Arduino e executa ações no sistema operacional e no OBS Studio via WebSocket.

### Funcionalidades

- 🎬 **Controle do OBS Studio** — Trocar cenas, alternar fontes, mudo, iniciar/parar streaming e gravação, câmera virtual, volume de fontes de áudio
- 🖥 **Controle do Windows** — Volume do sistema, teclas de mídia (play/pause/next/prev), atalhos de teclado customizados, abrir programas, executar comandos
- 🗂 **Sistema de Layouts** — Múltiplos layouts independentes (ex: "OBS Streaming", "Windows", "Gaming") com troca pelo software ou por um botão do próprio deck
- 🔧 **Totalmente Configurável** — Cada botão e potenciômetro pode ser mapeado para qualquer ação disponível através da interface gráfica
- 🌙 **Interface Dark Mode** — Tema escuro moderno com feedback visual em tempo real
- 📌 **System Tray** — Minimiza para a bandeja do sistema com menu de acesso rápido
- 💾 **Banco de Dados Seguro** — Dados e configurações salvas em SQLite com sistema de migração e versionamento de schema
- 🔄 **Auto-Updater** — Verificação e atualização automática da aplicação integrada com GitHub Releases (com backup)
- 🧪 **Alta Confiabilidade** — Bateria de testes unitários baseada em Mocks cobrindo as lógicas centrais e regras de negócio

---

## 🏗 Arquitetura

```
┌─────────────────┐      Serial USB       ┌──────────────────────────────────┐
│  Arduino Pro    │     (115200 baud)      │     Aplicação Desktop (Python)   │
│  Micro          │ ────────────────────── │                                  │
│                 │   Protocolo texto:     │  SerialWorker (QThread)          │
│  Matriz 3×5    │   B:linha,coluna,estado │       │                          │
│  + 3 Pots       │   P:indice,valor       │       ▼                          │
│                 │                        │  ActionDispatcher                │
└─────────────────┘                        │       │         │                │
                                           │       ▼         ▼                │
                                           │  OBSController  SystemController│
                                           │  (WebSocket v5) (volume/teclas) │
                                           │                                  │
                                           │  ProfileManager (layouts JSON)   │
                                           │  GUI PySide6 + System Tray       │
                                           └──────────────────────────────────┘
```

---

## ⚡ Hardware

### 📦 Case 3D

O modelo 3D oficial para impressão da case (gabinete) deste projeto está disponível no Cults3D:
👉 **[Download do Modelo 3D da Case](https://cults3d.com/pt/modelo-3d/diversos/stream-deck-cleberfonseca)**

### Componentes

| Componente | Quantidade | Descrição |
|---|---|---|
| Arduino Pro Micro (ATmega32U4) | 1 | Controlador com USB nativo |
| Botões tácteis (push button) | 15 | Matriz 3 linhas × 5 colunas |
| Potenciômetros lineares (10kΩ) | 3 | Controle analógico contínuo |
| Diodos 1N4148 (opcional) | 15 | Anti-ghosting na matriz |

### Pinagem do Arduino

| Função | Pinos |
|---|---|
| Linhas da matriz (OUTPUT) | 2, 3, 4 |
| Colunas da matriz (INPUT_PULLUP) | 5, 6, 7, 8, 9 |
| Potenciômetros (ANALOG) | A0, A1, A2 |

---

## 🚀 Instalação e Uso

### 1. Firmware Arduino

1. Abra o arquivo `arduino/streamdeck/streamdeck.ino` no **Arduino IDE**
2. Selecione a placa **Arduino Leonardo** (compatível com Pro Micro)
3. Selecione a porta serial correta
4. Faça o upload do código

### 2. Aplicação Desktop

#### Pré-requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes Python)

#### Instalação

```bash
# Clone o repositório
git clone https://github.com/clebersfonseca/StreamDeckDIY.git
cd StreamDeck

# Crie e ative o ambiente virtual
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

#### Dependência adicional para Windows (controle preciso de volume)

```bash
pip install pycaw comtypes
```

#### Executar

```bash
python -m app.main
```

---

## 🎮 Como Usar

### Primeira Execução

1. **Conecte o Arduino** ao computador via USB
2. **Abra a aplicação** (`python -m app.main`)
3. Vá para a aba **⚙ Configurações**:
   - Selecione a **porta serial** do Arduino e clique em **Conectar**
   - Configure o **OBS WebSocket** (host, porta, senha) e clique em **Conectar**
4. Vá para a aba **🎛 Mapeamento**:
   - Clique em qualquer **botão** da grade para configurar sua ação
   - Clique no **⚙** de um potenciômetro para configurar sua ação
5. Pronto! Os botões e potenciômetros agora executam as ações configuradas

### Gerenciamento de Layouts

- Use a **barra superior** da janela para criar, duplicar, renomear ou excluir layouts
- Troque entre layouts pelo **dropdown**, pelo **menu do system tray**, ou mapeando um botão do deck com a ação **"App: Trocar Layout"**

---

## 📁 Estrutura do Projeto

```
StreamDeck/
├── arduino/
│   └── streamdeck/
│       └── streamdeck.ino           # Firmware do Arduino Pro Micro
├── app/
│   ├── main.py                      # Entry point da aplicação
│   ├── core/
│   │   ├── serial_worker.py         # QThread para comunicação serial
│   │   ├── profile_manager.py       # Gerenciador de layouts e configurações
│   │   ├── action_dispatcher.py     # Roteador de eventos → ações
│   │   ├── obs_controller.py        # Integração OBS WebSocket v5
│   │   ├── system_controller.py     # Controle do SO (volume, teclas, apps)
│   │   ├── database.py              # Motor do banco de dados e Runner de migrações
│   │   ├── updater.py               # Checagem e download de atualizações via GitHub API
│   │   └── migrations/              # Scripts de versionamento do banco de dados (estilo Django)
│   ├── gui/
│   │   ├── main_window.py           # Janela principal (3 abas)
│   │   ├── button_grid.py           # Widget da grade 3×5
│   │   ├── pot_widget.py            # Widget dos potenciômetros
│   │   ├── action_dialog.py         # Diálogo de configuração de ação
│   │   ├── tray_icon.py             # Ícone na bandeja do sistema
│   │   └── styles.py                # Tema dark mode
│   └── config/
│       └── streamdeck.db            # Banco de dados SQLite principal (auto-gerado, não versionado)
├── tests/                           # Suíte de testes automatizados (pytest)
├── requirements.txt                 # Dependências Python
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🛠 Ações Disponíveis

### OBS Studio

| Ação | Descrição | Tipo |
|---|---|---|
| Trocar Cena | Muda para uma cena específica | Botão |
| Alternar Fonte | Liga/desliga uma fonte em uma cena | Botão |
| Alternar Mudo | Muta/desmuta uma fonte de áudio | Botão |
| Iniciar/Parar Transmissão | Controla o streaming | Botão |
| Iniciar/Parar Gravação | Controla a gravação | Botão |
| Alternar Câmera Virtual | Liga/desliga a câmera virtual | Botão |
| Volume da Fonte | Ajusta volume de uma fonte de áudio | Potenciômetro |

### Sistema

| Ação | Descrição | Tipo |
|---|---|---|
| Volume +/−/Mudo | Controla o volume do sistema | Botão |
| Definir Volume | Define o volume exato (0-100%) | Potenciômetro |
| Play/Pause | Controle de mídia | Botão |
| Próxima/Anterior Faixa | Navega entre faixas de mídia | Botão |
| Atalho de Teclado | Executa qualquer combinação de teclas | Botão |
| Abrir Programa | Abre um programa pelo caminho | Botão |
| Executar Comando | Executa um comando no shell | Botão |

### Aplicação

| Ação | Descrição | Tipo |
|---|---|---|
| Trocar Layout | Muda para outro layout do StreamDeck | Botão |

---

## 📡 Protocolo Serial

Comunicação entre Arduino e PC via Serial USB a **115200 baud**.

| Evento | Formato | Exemplo |
|---|---|---|
| Botão pressionado | `B:<linha>,<coluna>,1` | `B:0,2,1` |
| Botão solto | `B:<linha>,<coluna>,0` | `B:1,4,0` |
| Potenciômetro | `P:<indice>,<valor>` | `P:0,512` |
| Arduino pronto | `READY` | — |

- Botões: linha `0-2`, coluna `0-4`
- Potenciômetros: índice `0-2`, valor `0-1023`

---

## 📦 Gerar Executável (Windows)

Para distribuir a aplicação sem precisar do Python instalado:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name StreamDeckDIY app/main.py
```

O executável será gerado em `dist/StreamDeckDIY.exe`.

> **Nota:** O build deve ser feito no Windows para gerar um `.exe` compatível.

---

## 🔧 Tecnologias

| Tecnologia | Uso |
|---|---|
| [Python 3.9+](https://www.python.org/) | Linguagem principal |
| [PySide6](https://doc.qt.io/qtforpython/) | Interface gráfica (Qt) |
| [pyserial](https://pyserial.readthedocs.io/) | Comunicação serial |
| [obsws-python](https://github.com/aatikturk/obsws-python) | OBS WebSocket v5 |
| [pyautogui](https://pyautogui.readthedocs.io/) | Simulação de teclas |
| [pycaw](https://github.com/AndreMiras/pycaw) | Controle de volume (Windows) |
| [Arduino IDE](https://www.arduino.cc/en/software) | Firmware do Arduino |

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um **fork** do projeto
2. Criar uma **branch** para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Fazer **commit** das alterações (`git commit -m 'Adiciona nova funcionalidade'`)
4. Fazer **push** para a branch (`git push origin feature/nova-funcionalidade`)
5. Abrir um **Pull Request**

---

## 📄 Licença

Este projeto está licenciado sob a **GNU General Public License v3.0** — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 📬 Contato

Se tiver dúvidas ou sugestões, abra uma [issue](../../issues) no repositório.
