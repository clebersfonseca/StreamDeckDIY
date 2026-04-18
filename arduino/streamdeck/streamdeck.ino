// ============================================================
// StreamDeck DIY - Arduino Pro Micro
// ============================================================
// Matriz de botões: 3 linhas x 5 colunas
//   Linhas (OUTPUT): pinos 2, 3, 4
//   Colunas (INPUT_PULLUP): pinos 5, 6, 7, 8, 9
//
// Potenciômetros: A0, A1, A2
//
// Protocolo Serial (115200 baud):
//   Botão pressionado:  "B:<linha>,<coluna>,1\n"
//   Botão solto:        "B:<linha>,<coluna>,0\n"
//   Potenciômetro:      "P:<indice>,<valor>\n"  (valor 0-1023)
// ============================================================

// ---- Configuração da Matriz ----
const byte NUM_LINHAS  = 3;
const byte NUM_COLUNAS = 5;

const byte pinosLinhas[NUM_LINHAS]   = { 2, 3, 4 };
const byte pinosColunas[NUM_COLUNAS] = { 5, 6, 7, 8, 9 };

// Estado atual e anterior de cada botão (para detectar mudanças)
bool estadoBotao[NUM_LINHAS][NUM_COLUNAS];
bool estadoAnterior[NUM_LINHAS][NUM_COLUNAS];

// ---- Configuração dos Potenciômetros ----
const byte NUM_POTS = 3;
const byte pinosPots[NUM_POTS] = { A0, A1, A2 };

int valorPot[NUM_POTS];
int valorPotAnterior[NUM_POTS];

// Limiar mínimo de variação para enviar atualização do potenciômetro.
// Evita ruído e envio desnecessário de dados.
const int LIMIAR_POT = 5;

// ---- Debounce ----
// Tempo mínimo (ms) entre leituras da matriz para debounce dos botões.
const unsigned long DEBOUNCE_MS = 10;
unsigned long ultimoScan = 0;

// Intervalo de leitura dos potenciômetros (ms)
const unsigned long INTERVALO_POT_MS = 20;
unsigned long ultimaLeituraPot = 0;

// ============================================================
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // Aguarda conexão serial (necessário no Pro Micro / Leonardo)
  }

  // Configura pinos das linhas como OUTPUT (HIGH por padrão)
  for (byte i = 0; i < NUM_LINHAS; i++) {
    pinMode(pinosLinhas[i], OUTPUT);
    digitalWrite(pinosLinhas[i], HIGH);
  }

  // Configura pinos das colunas como INPUT_PULLUP
  for (byte j = 0; j < NUM_COLUNAS; j++) {
    pinMode(pinosColunas[j], INPUT_PULLUP);
  }

  // Inicializa estados dos botões
  for (byte i = 0; i < NUM_LINHAS; i++) {
    for (byte j = 0; j < NUM_COLUNAS; j++) {
      estadoBotao[i][j]    = false;
      estadoAnterior[i][j] = false;
    }
  }

  // Leitura inicial dos potenciômetros
  for (byte p = 0; p < NUM_POTS; p++) {
    valorPot[p]         = analogRead(pinosPots[p]);
    valorPotAnterior[p] = valorPot[p];
  }

  // Sinal de que o Arduino está pronto
  Serial.println("READY");
}

// ============================================================
void loop() {
  unsigned long agora = millis();

  // ---- Varredura da Matriz de Botões ----
  if (agora - ultimoScan >= DEBOUNCE_MS) {
    ultimoScan = agora;
    varrerMatriz();
  }

  // ---- Leitura dos Potenciômetros ----
  if (agora - ultimaLeituraPot >= INTERVALO_POT_MS) {
    ultimaLeituraPot = agora;
    lerPotenciometros();
  }
}

// ============================================================
// Varre a matriz de botões linha por linha.
// Técnica: coloca cada linha em LOW, lê todas as colunas.
// Se a coluna estiver LOW, o botão está pressionado.
// ============================================================
void varrerMatriz() {
  for (byte i = 0; i < NUM_LINHAS; i++) {
    // Ativa a linha atual (LOW)
    digitalWrite(pinosLinhas[i], LOW);

    // Pequeno atraso para estabilizar o sinal
    delayMicroseconds(50);

    for (byte j = 0; j < NUM_COLUNAS; j++) {
      // LOW = botão pressionado (pull-up ativo)
      bool pressionado = (digitalRead(pinosColunas[j]) == LOW);
      estadoBotao[i][j] = pressionado;

      // Detecta mudança de estado
      if (estadoBotao[i][j] != estadoAnterior[i][j]) {
        enviarEventoBotao(i, j, pressionado);
        estadoAnterior[i][j] = estadoBotao[i][j];
      }
    }

    // Desativa a linha (HIGH)
    digitalWrite(pinosLinhas[i], HIGH);
  }
}

// ============================================================
// Lê os potenciômetros e envia atualização quando a variação
// excede o limiar definido (LIMIAR_POT).
// ============================================================
void lerPotenciometros() {
  for (byte p = 0; p < NUM_POTS; p++) {
    valorPot[p] = analogRead(pinosPots[p]);

    int diferenca = abs(valorPot[p] - valorPotAnterior[p]);

    if (diferenca >= LIMIAR_POT) {
      enviarEventoPot(p, valorPot[p]);
      valorPotAnterior[p] = valorPot[p];
    }
  }
}

// ============================================================
// Envia evento de botão via Serial
// Formato: B:<linha>,<coluna>,<estado>
//   estado: 1 = pressionado, 0 = solto
// ============================================================
void enviarEventoBotao(byte linha, byte coluna, bool pressionado) {
  Serial.print("B:");
  Serial.print(linha);
  Serial.print(",");
  Serial.print(coluna);
  Serial.print(",");
  Serial.println(pressionado ? 1 : 0);
}

// ============================================================
// Envia evento de potenciômetro via Serial
// Formato: P:<indice>,<valor>
//   valor: 0 a 1023
// ============================================================
void enviarEventoPot(byte indice, int valor) {
  Serial.print("P:");
  Serial.print(indice);
  Serial.print(",");
  Serial.println(valor);
}
