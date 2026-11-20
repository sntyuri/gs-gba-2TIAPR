/*
 * ============================================================================
 *  CitizenTech · Monitor de Pavimento: firmware do ESP32 (sensores reais)
 * ============================================================================
 *  ESP32 instalado em um veículo de serviço (ou na maquete) que mede a via:
 *
 *   - VL53L0X (ToF, I2C) ...... aponta para o solo. A diferença entre a
 *                               distância medida e a altura calibrada sobre
 *                               piso plano é a PROFUNDIDADE do buraco.
 *   - DHT22 ................... temperatura e umidade do ar. Umidade alta indica
 *                               pista molhada: a infiltração de água acelera a
 *                               formação de buracos e aumenta o risco.
 *   - Botão ................... reporte manual do motorista ("passei num buraco").
 *   - LEDs .................... ação local: verde = ok, amarelo = atenção,
 *                               vermelho = buraco grave / trecho crítico.
 *   - Trecho da via ........... o protótipo não tem GPS: o trecho atual chega
 *                               por comando MQTT (iot/definir_trecho.py) ou pelo
 *                               Serial Monitor ("trecho SIM0002").
 *
 *  Fluxo de dados (o mesmo que alimenta a IA generativa):
 *    sensores -> ESP32 -> MQTT -> iot/receptor_mqtt.py -> citizentech.db
 *             -> vw_prioridade_trechos -> agente GenAI (relatório / chat)
 *  O ESP32 também ASSINA o tópico de comando para receber do back-end o alerta
 *  de trecho crítico (LED vermelho piscando), a troca de trecho e a recalibração.
 *
 *  Tópicos: <TOPICO_BASE>/<DEVICE_ID>/{leitura, evento, status, comando}
 *
 *  Ligações (ESP32 DevKit):
 *    VL53L0X  VIN->3V3  GND->GND  SDA->GPIO21  SCL->GPIO22
 *    DHT22    VCC->3V3  DATA->GPIO4 (10k para 3V3 se o módulo não tiver)  GND->GND
 *    Botão    GPIO13 <-> GND (pull-up interno)
 *    LEDs     GPIO25 (verde), GPIO26 (amarelo), GPIO33 (vermelho) -> 220R -> GND
 * ============================================================================
 */
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <VL53L0X.h>
#include <DHT.h>
#include <time.h>

// ---- Credenciais e rede: defina em include/credenciais.h (fora do Git) ----
#if __has_include("credenciais.h")
#include "credenciais.h"
#endif
#ifndef WIFI_SSID
#define WIFI_SSID "SUA_REDE"
#endif
#ifndef WIFI_SENHA
#define WIFI_SENHA "SUA_SENHA"
#endif
#ifndef MQTT_HOST
#define MQTT_HOST "broker.hivemq.com"          // broker público de testes
#endif
#ifndef MQTT_PORTA
#define MQTT_PORTA 1883
#endif
#ifndef TOPICO_BASE
#define TOPICO_BASE "fiap/citizentech/gohorse-gs2026"   // MESMO valor do config.py
#endif
#ifndef DEVICE_ID
#define DEVICE_ID "esp32-01"
#endif
#ifndef TRECHO_INICIAL
#define TRECHO_INICIAL "SIM0001"
#endif

// ---- Pinos ----
#define PIN_SDA           21
#define PIN_SCL           22
#define PIN_DHT           4
#define PIN_BOTAO         13
#define PIN_LED_VERDE     25
#define PIN_LED_AMARELO   26
#define PIN_LED_VERMELHO  33

// ---- Limiares (escala da maquete, em milímetros) ----
const int   LIMIAR_LEVE_MM    = 15;    // a partir daqui: irregularidade leve
const int   LIMIAR_GRAVE_MM   = 40;    // a partir daqui: buraco grave
const int   HISTERESE_MM      = 5;     // evita "piscar" na borda do limiar
const int   MIN_AMOSTRAS      = 2;     // leituras seguidas acima do limiar
const float UMIDADE_ALTA      = 85.0;  // %: pista possivelmente molhada
const int   DIST_MAX_VALIDA   = 2000;  // mm; acima disso é "fora de alcance"

const unsigned long INTERVALO_VL_MS        = 50;    // leitura do ToF (~20 Hz)
const unsigned long INTERVALO_LEITURA_MS   = 5000;  // telemetria periódica
const unsigned long INTERVALO_RETRY_VL_MS  = 5000;  // nova tentativa se o VL53L0X sumir
const int           MAX_TIMEOUTS_VL        = 20;    // timeouts seguidos = sensor desconectado

VL53L0X vl;
DHT dht(PIN_DHT, DHT22);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

char topicoLeitura[96], topicoEvento[96], topicoComando[96], topicoStatus[96];

// ---- Estado dos sensores ----
bool  vlOk = false;
int   timeoutsVl = 0;
int   baselineMm = 0;            // altura do sensor até o solo plano (calibrada)
int   distanciaMm = -1;
int   profundidadeMm = 0;
float temperatura = NAN, umidade = NAN;
int   falhasDht = 0;             // leituras inválidas seguidas do DHT22
char  trechoAtual[24] = "";

// Filtro de mediana de 3 amostras: remove picos isolados do ToF
int janela[3] = {0, 0, 0};
int nJanela = 0, idxJanela = 0;

// Máquina de estados da detecção
bool  emIrregularidade = false;
int   amostrasAcima = 0;
int   profMaxMm = 0;
unsigned long ultimoEventoMs = 0;
char  ultimaSeveridade[8] = "ok";

unsigned long ultimoVlMs = 0, ultimaLeituraMs = 0, ultimaTentativaMqtt = 0, ultimaTentativaVl = 0;
unsigned long confirmacaoAteMs = 0, alertaRemotoAteMs = 0;
bool  botaoAnterior = HIGH;
unsigned long botaoMudouMs = 0;

// Fila de eventos: se o MQTT cair (veículo sem sinal), os eventos são guardados
// e reenviados na reconexão. Ao encher, descarta o mais antigo.
const int FILA_MAX = 12;
char fila[FILA_MAX][320];
int  filaInicio = 0, filaTamanho = 0;

// ---- protótipos ----
void publicarEvento(const char* tipo, const char* severidade, int prof);
void calibrar();
void definirTrecho(const char* codigo, bool avisar);

// ============================== utilitários =================================
void fmtFloat(char* out, size_t n, float v) {
  if (isnan(v)) snprintf(out, n, "null"); else snprintf(out, n, "%.1f", v);
}

void fmtTrecho(char* out, size_t n) {
  if (trechoAtual[0]) snprintf(out, n, "\"%s\"", trechoAtual); else snprintf(out, n, "null");
}

unsigned long agoraEpoch() {             // 0 se o NTP ainda não sincronizou
  time_t t = time(nullptr);
  return t > 1700000000 ? (unsigned long)t : 0;
}

void confirmar(unsigned long ms) { confirmacaoAteMs = millis() + ms; }   // 3 LEDs acesos

bool dhtOk() { return falhasDht < 3 && !isnan(umidade); }
bool pistaUmida() { return dhtOk() && umidade >= UMIDADE_ALTA; }

const char* statusAtual() {
  if (ultimoEventoMs > 0 && millis() - ultimoEventoMs < 3000) return ultimaSeveridade;
  if (emIrregularidade) return profMaxMm >= LIMIAR_GRAVE_MM ? "grave" : "leve";
  return "ok";
}

int mediana3(int novo) {
  janela[idxJanela] = novo;
  idxJanela = (idxJanela + 1) % 3;
  if (nJanela < 3) nJanela++;
  if (nJanela < 3) return novo;
  int a = janela[0], b = janela[1], c = janela[2];
  return max(min(a, b), min(max(a, b), c));
}

// ============================== MQTT: publicação ============================
void enfileirar(const char* json) {
  if (filaTamanho == FILA_MAX) {                       // cheia: descarta o mais antigo
    filaInicio = (filaInicio + 1) % FILA_MAX;
    filaTamanho--;
  }
  int pos = (filaInicio + filaTamanho) % FILA_MAX;
  strncpy(fila[pos], json, sizeof fila[pos] - 1);
  fila[pos][sizeof fila[pos] - 1] = '\0';
  filaTamanho++;
}

void descarregarFila() {
  while (filaTamanho > 0 && mqtt.connected()) {
    if (!mqtt.publish(topicoEvento, fila[filaInicio])) break;
    Serial.printf("[EVENTO REENVIADO] %s\n", fila[filaInicio]);
    filaInicio = (filaInicio + 1) % FILA_MAX;
    filaTamanho--;
  }
}

void publicarEvento(const char* tipo, const char* severidade, int prof) {
  char t[12], u[12], tr[30], json[320];
  fmtFloat(t, sizeof t, temperatura);
  fmtFloat(u, sizeof u, umidade);
  fmtTrecho(tr, sizeof tr);
  snprintf(json, sizeof json,
    "{\"device\":\"%s\",\"tipo\":\"%s\",\"severidade\":\"%s\",\"trecho\":%s,"
    "\"prof_mm\":%d,\"temp_c\":%s,\"umid\":%s,\"ts\":%lu}",
    DEVICE_ID, tipo, severidade, tr, prof, t, u, agoraEpoch());
  bool ok = mqtt.connected() && mqtt.publish(topicoEvento, json);
  if (!ok) enfileirar(json);
  Serial.printf("[EVENTO%s] %s\n", ok ? "" : " NA FILA", json);
}

void publicarLeitura() {
  char t[12], u[12], tr[30], json[384];
  fmtFloat(t, sizeof t, temperatura);
  fmtFloat(u, sizeof u, umidade);
  fmtTrecho(tr, sizeof tr);
  snprintf(json, sizeof json,
    "{\"device\":\"%s\",\"trecho\":%s,\"dist_mm\":%d,\"prof_mm\":%d,"
    "\"temp_c\":%s,\"umid\":%s,\"pista_umida\":%s,\"status\":\"%s\","
    "\"vl_ok\":%s,\"dht_ok\":%s,\"base_mm\":%d,\"rssi\":%d,\"ts\":%lu}",
    DEVICE_ID, tr, distanciaMm, profundidadeMm, t, u,
    pistaUmida() ? "true" : "false", statusAtual(),
    vlOk ? "true" : "false", dhtOk() ? "true" : "false", baselineMm,
    WiFi.status() == WL_CONNECTED ? (int)WiFi.RSSI() : 0, agoraEpoch());
  bool ok = mqtt.connected() && mqtt.publish(topicoLeitura, json);
  Serial.printf("[LEITURA%s] %s\n", ok ? "" : " NAO ENVIADA", json);
}

// ============================== sensores ====================================
bool iniciarVl() {
  vl.setTimeout(500);
  if (!vl.init()) return false;
  vl.setMeasurementTimingBudget(33000);   // 33 ms: bom equilíbrio precisão × taxa
  vl.startContinuous();                   // mede sem parar; a leitura só busca o último valor
  timeoutsVl = 0;
  nJanela = idxJanela = 0;
  return true;
}

void calibrar() {
  if (!vlOk) {
    Serial.println("Calibracao ignorada: VL53L0X ausente.");
    return;
  }
  Serial.println("Calibrando: mantenha o sensor sobre superficie PLANA...");
  digitalWrite(PIN_LED_AMARELO, HIGH);
  long soma = 0; int n = 0;
  for (int i = 0; i < 30; i++) {
    uint16_t d = vl.readRangeContinuousMillimeters();
    if (!vl.timeoutOccurred() && d > 0 && d < DIST_MAX_VALIDA) { soma += d; n++; }
    delay(35);
  }
  digitalWrite(PIN_LED_AMARELO, LOW);
  if (n >= 10) {
    baselineMm = soma / n;
    emIrregularidade = false; amostrasAcima = 0; profMaxMm = 0;
    Serial.printf("Altura de referencia: %d mm (%d amostras)\n", baselineMm, n);
    publicarEvento("calibracao", "info", baselineMm);
  } else {
    Serial.println("Calibracao falhou (leituras invalidas). Use o comando \"calibrar\".");
  }
}

void processarProfundidade(int prof) {
  if (!emIrregularidade) {
    if (prof >= LIMIAR_LEVE_MM) {
      amostrasAcima++;
      profMaxMm = max(profMaxMm, prof);
      if (amostrasAcima >= MIN_AMOSTRAS) emIrregularidade = true;
    } else {
      amostrasAcima = 0;
      profMaxMm = 0;
    }
    return;
  }
  // Dentro da irregularidade: acompanha a profundidade máxima e, quando o
  // sensor volta ao nível normal, emite UM evento por passagem pelo buraco.
  profMaxMm = max(profMaxMm, prof);
  if (prof < LIMIAR_LEVE_MM - HISTERESE_MM) {
    const char* sev = profMaxMm >= LIMIAR_GRAVE_MM ? "grave" : "leve";
    strncpy(ultimaSeveridade, sev, sizeof ultimaSeveridade);
    ultimoEventoMs = millis();
    publicarEvento("buraco", sev, profMaxMm);
    emIrregularidade = false;
    amostrasAcima = 0;
    profMaxMm = 0;
  }
}

void lerDistancia() {
  uint16_t d = vl.readRangeContinuousMillimeters();
  if (vl.timeoutOccurred()) {
    if (++timeoutsVl >= MAX_TIMEOUTS_VL) {
      vlOk = false;
      Serial.println("ERRO: VL53L0X parou de responder (verifique os fios). Tentando reconectar...");
    }
    return;
  }
  timeoutsVl = 0;
  if (d == 0 || d >= DIST_MAX_VALIDA) return;            // fora de alcance
  distanciaMm = mediana3(d);
  profundidadeMm = max(0, distanciaMm - baselineMm);     // ressaltos (lombadas) = 0
  processarProfundidade(profundidadeMm);
}

void lerDht() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (isnan(t) || isnan(h)) {
    if (++falhasDht == 3) Serial.println("AVISO: DHT22 sem leitura valida (verifique DATA no GPIO4).");
    return;                                  // mantém o último valor válido
  }
  falhasDht = 0;
  temperatura = t;
  umidade = h;
}

void lerBotao() {
  bool leitura = digitalRead(PIN_BOTAO);
  if (leitura != botaoAnterior && millis() - botaoMudouMs > 50) {   // debounce
    botaoMudouMs = millis();
    botaoAnterior = leitura;
    if (leitura == LOW) {
      confirmar(300);
      publicarEvento("reporte_manual", "info", profundidadeMm);
    }
  }
}

void atualizarLeds() {
  if (millis() < confirmacaoAteMs) {     // confirmação: os três acesos
    digitalWrite(PIN_LED_VERMELHO, HIGH);
    digitalWrite(PIN_LED_AMARELO, HIGH);
    digitalWrite(PIN_LED_VERDE, HIGH);
    return;
  }
  const char* s = statusAtual();
  bool remoto = millis() < alertaRemotoAteMs;
  bool vermelho = strcmp(s, "grave") == 0 || (remoto && (millis() / 250) % 2 == 0);
  bool amarelo = !vermelho && !remoto && (strcmp(s, "leve") == 0 || pistaUmida());
  bool verde = !vermelho && !amarelo && !remoto;
  digitalWrite(PIN_LED_VERMELHO, vermelho);
  digitalWrite(PIN_LED_AMARELO, amarelo);
  digitalWrite(PIN_LED_VERDE, verde);
}

// ============================== trecho (GPS simulado) =======================
void definirTrecho(const char* codigo, bool avisar) {
  while (*codigo == ' ') codigo++;
  if (!codigo[0] || strcmp(codigo, trechoAtual) == 0) return;
  strncpy(trechoAtual, codigo, sizeof trechoAtual - 1);
  trechoAtual[sizeof trechoAtual - 1] = '\0';
  for (char* p = trechoAtual; *p; p++) *p = toupper(*p);
  Serial.printf("Trecho atual: %s\n", trechoAtual);
  if (avisar) {
    confirmar(300);
    publicarEvento("mudanca_trecho", "info", 0);
  }
}

// ============================== MQTT: comandos ==============================
// Extrai o valor texto de "chave" num JSON simples: {"chave": "valor", ...}
bool extrairCampo(const char* json, const char* chave, char* out, size_t n) {
  char padrao[24];
  snprintf(padrao, sizeof padrao, "\"%s\"", chave);
  const char* p = strstr(json, padrao);
  if (!p) return false;
  p = strchr(p + strlen(padrao), ':');
  if (!p) return false;
  p = strchr(p, '"');
  if (!p) return false;
  p++;
  size_t i = 0;
  while (*p && *p != '"' && i < n - 1) out[i++] = *p++;
  out[i] = '\0';
  return i > 0;
}

void aoReceberComando(char* topic, byte* payload, unsigned int len) {
  char msg[256], acao[16], valor[24];
  if (len >= sizeof msg) len = sizeof msg - 1;
  memcpy(msg, payload, len);
  msg[len] = '\0';
  Serial.printf("[COMANDO] %s\n", msg);
  if (!extrairCampo(msg, "acao", acao, sizeof acao)) return;

  if (strcmp(acao, "trecho") == 0) {              // {"acao":"trecho","codigo":"SIM0002"}
    if (extrairCampo(msg, "codigo", valor, sizeof valor)) definirTrecho(valor, true);
  } else if (strcmp(acao, "calibrar") == 0) {
    calibrar();
  } else if (strcmp(acao, "alerta") == 0) {       // trecho crítico à frente
    alertaRemotoAteMs = millis() + 5000;
    publicarEvento("alerta_recebido", "info", 0);
  } else if (strcmp(acao, "ping") == 0) {
    publicarEvento("online", "info", 0);
  }
}

void conectarMqtt() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (millis() - ultimaTentativaMqtt < 3000) return;
  ultimaTentativaMqtt = millis();
  char id[40];
  snprintf(id, sizeof id, "%s-%04X", DEVICE_ID, (unsigned)(esp_random() & 0xFFFF));
  // Last Will: se o ESP32 cair, o broker publica "offline" no tópico de status
  if (mqtt.connect(id, topicoStatus, 1, true, "offline")) {
    mqtt.publish(topicoStatus, "online", true);
    mqtt.subscribe(topicoComando);
    Serial.printf("MQTT conectado a %s (base %s).\n", MQTT_HOST, TOPICO_BASE);
    descarregarFila();
  } else {
    Serial.printf("MQTT falhou (rc=%d), tentando de novo...\n", mqtt.state());
  }
}

// ============================== Serial Monitor ==============================
void imprimirStatus() {
  Serial.printf("--- %s | trecho %s ---\n", DEVICE_ID, trechoAtual[0] ? trechoAtual : "-");
  Serial.printf("Wi-Fi: %s (RSSI %d) | MQTT: %s | eventos na fila: %d\n",
                WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "desconectado",
                WiFi.status() == WL_CONNECTED ? (int)WiFi.RSSI() : 0,
                mqtt.connected() ? "conectado" : "desconectado", filaTamanho);
  Serial.printf("VL53L0X: %s | base %d mm | distancia %d mm | profundidade %d mm\n",
                vlOk ? "ok" : "AUSENTE", baselineMm, distanciaMm, profundidadeMm);
  Serial.printf("DHT22: %s | %.1f C | %.1f %%\n", dhtOk() ? "ok" : "SEM LEITURA", temperatura, umidade);
}

void processarLinhaSerial(char* linha) {
  if (strncmp(linha, "trecho ", 7) == 0) definirTrecho(linha + 7, true);
  else if (strcmp(linha, "calibrar") == 0) calibrar();
  else if (strcmp(linha, "status") == 0) imprimirStatus();
  else if (strcmp(linha, "reporte") == 0) { confirmar(300); publicarEvento("reporte_manual", "info", profundidadeMm); }
  else if (linha[0]) Serial.println("Comandos: trecho <codigo> | calibrar | status | reporte");
}

void lerSerial() {
  static char buf[48];
  static size_t n = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') { buf[n] = '\0'; processarLinhaSerial(buf); n = 0; }
    else if (n < sizeof buf - 1) buf[n++] = c;
  }
}

// ============================== setup / loop ================================
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\nCitizenTech · Monitor de Pavimento: " DEVICE_ID);
  pinMode(PIN_BOTAO, INPUT_PULLUP);
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_AMARELO, OUTPUT);
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  digitalWrite(PIN_LED_AMARELO, HIGH);    // amarelo fixo = inicializando

  Wire.begin(PIN_SDA, PIN_SCL);
  vlOk = iniciarVl();
  Serial.println(vlOk ? "VL53L0X ok." : "ERRO: VL53L0X nao encontrado (verifique SDA/SCL e 3V3).");
  ultimaTentativaVl = millis();

  dht.begin();
  definirTrecho(TRECHO_INICIAL, false);

  snprintf(topicoLeitura, sizeof topicoLeitura, "%s/%s/leitura", TOPICO_BASE, DEVICE_ID);
  snprintf(topicoEvento,  sizeof topicoEvento,  "%s/%s/evento",  TOPICO_BASE, DEVICE_ID);
  snprintf(topicoComando, sizeof topicoComando, "%s/%s/comando", TOPICO_BASE, DEVICE_ID);
  snprintf(topicoStatus,  sizeof topicoStatus,  "%s/%s/status",  TOPICO_BASE, DEVICE_ID);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  Serial.printf("Conectando ao Wi-Fi \"%s\"", WIFI_SSID);
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++) { delay(500); Serial.print("."); }
  Serial.println(WiFi.status() == WL_CONNECTED ? " ok" : " FALHOU (seguindo offline; eventos vao para a fila)");

  configTime(-3 * 3600, 0, "pool.ntp.org", "time.google.com");    // horário de Brasília

  mqtt.setServer(MQTT_HOST, MQTT_PORTA);
  mqtt.setCallback(aoReceberComando);
  mqtt.setBufferSize(512);               // o padrão (256 B) é pequeno para o JSON
  for (int i = 0; i < 5 && !mqtt.connected() && WiFi.status() == WL_CONNECTED; i++) {
    ultimaTentativaMqtt = 0;
    conectarMqtt();
    if (!mqtt.connected()) delay(1000);
  }

  calibrar();
  lerDht();
  digitalWrite(PIN_LED_AMARELO, LOW);
  Serial.println("Pronto. Digite \"ajuda\" no Serial Monitor para ver os comandos.");
}

void loop() {
  conectarMqtt();
  mqtt.loop();
  lerSerial();

  unsigned long agora = millis();

  // VL53L0X desconectado: tenta de novo periodicamente e recalibra
  if (!vlOk && agora - ultimaTentativaVl >= INTERVALO_RETRY_VL_MS) {
    ultimaTentativaVl = agora;
    if ((vlOk = iniciarVl())) {
      Serial.println("VL53L0X reconectado.");
      calibrar();
    }
  }
  if (vlOk && baselineMm > 0 && agora - ultimoVlMs >= INTERVALO_VL_MS) {
    ultimoVlMs = agora;
    lerDistancia();
  }
  lerBotao();

  if (agora - ultimaLeituraMs >= INTERVALO_LEITURA_MS) {
    ultimaLeituraMs = agora;
    lerDht();
    publicarLeitura();
  }

  atualizarLeds();
}
