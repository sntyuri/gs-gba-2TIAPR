## Sumário
1. Problema, público beneficiado e relevância
2. Visão geral da solução integrada
3. Arquitetura do módulo IoT e origem dos dados
4. Comunicação MQTT
5. Armazenamento e uso dos dados
6. Testes e evidências de funcionamento
7. Implementado, simulado e limitações
8. Relação com os ODS
9. Referências
Apêndice A. Código-fonte

# 1. Problema, público beneficiado e relevância

Buracos e irregularidades no asfalto causam acidentes, danos a veículos e quedas de motociclistas e ciclistas. Também tornam o transporte público mais lento e desconfortável. Hoje, na maior parte das cidades, a prefeitura só toma conhecimento de um buraco quando alguém reclama, por exemplo pelo SP156. O processo é reativo: a solicitação chega depois que o problema já existe, sem medida objetiva de gravidade e sem um critério claro para priorizar as vistorias.

A proposta do Monitor de Pavimento é coletar esses dados de forma contínua e automática. A coleta usa veículos que já circulam pela cidade todos os dias (ônibus, viaturas da zeladoria, caminhões de coleta), equipados com um dispositivo IoT de baixo custo.

**Público beneficiado**

- **Cidadãos que usam as vias:** motoristas, motociclistas, ciclistas, pedestres e passageiros de ônibus. Eles se beneficiam de vias mais seguras e de reparos mais rápidos nos pontos críticos.
- **Equipes municipais de zeladoria e subprefeituras:** recebem uma lista priorizada de trechos para inspeção, com base em medidas objetivas e não apenas no volume de reclamações.

**Evidências de relevância**

- Na cidade de São Paulo foram registrados quase 52 mil pedidos de tapa-buraco no 1º semestre de 2026, cerca de 287 por dia. A série anual foi de 177,3 mil pedidos em 2023 e 113,1 mil em 2025, segundo dados da Secretaria Municipal das Subprefeituras divulgados pela imprensa [1].
- A chuva acelera o surgimento de buracos. Em setembro de 2026, São José dos Campos atendeu 30% mais pedidos de tapa-buraco depois de um período de chuvas intensas, que desgastam o asfalto [2]. Essa relação justifica o uso do sensor de umidade no projeto.
- A Pesquisa CNT de Rodovias 2026 avaliou 115 mil km de vias pavimentadas e encontrou 57,2% com alguma deficiência no pavimento. O pavimento inadequado eleva o custo operacional dos transportadores em média 31,8%, o equivalente a cerca de R$ 6,2 bilhões em diesel extra [3]. O dado é de rodovias, mas mostra o impacto econômico do pavimento em mau estado.
- O Código de Trânsito Brasileiro (art. 1º, §3º) atribui ao poder público o dever de garantir um trânsito seguro. Municípios são frequentemente condenados a indenizar danos causados por buracos [4]. Detectar cedo reduz riscos às pessoas e custos ao município.

# 2. Visão geral da solução integrada

O CitizenTech é uma solução única, desenvolvida em três disciplinas que compartilham o mesmo problema, público e banco de dados. Este relatório trata do módulo IoT. Os módulos de Visão Computacional e de IA Generativa são documentados nas respectivas entregas.

```
   Módulo IoT                                        Visão computacional
   ESP32 · sensores · MQTT                           YOLO em fotos e vídeos
          │   ▲                                               │
          │   │ comandos MQTT (alerta / trecho)               │
          ▼   │                                               ▼
   ┌──────────┴───────────────────────────────────────────────────┐
   │        Banco compartilhado · prioridade por trecho           │
   └──────────────────────────────┬───────────────────────────────┘
                                  ▼
                           Agente GenAI
              LLM open source local · RAG · ferramentas
                    │                         │
        Prefeitura (zeladoria)             Cidadão
        ranking e rota de inspeção         dúvidas e reportes
```
Figura 1. Arquitetura integrada. IoT e Visão gravam no banco; o agente GenAI lê o banco, atende prefeitura e cidadão e pode enviar comandos ao ESP32.

| Módulo | Papel na solução | Ligação com os demais |
|---|---|---|
| IoT (este documento) | Mede a via em movimento: profundidade de buracos, condição climática e reportes do motorista. | Grava leituras e eventos no banco. Recebe comandos do servidor. |
| Visão computacional | Detecta buracos em fotos e vídeos (YOLO) e mostra a confiança do modelo. | Grava cada detecção no banco, associada ao trecho. |
| IA generativa | Agente que cruza os dados, gera o relatório de inspeção priorizado e responde o cidadão com RAG. | Lê a view de prioridade e pode publicar comandos MQTT. |

# 3. Arquitetura do módulo IoT e origem dos dados

O fluxo pedido no enunciado (Entrada → ESP32 → MQTT → uso dos dados) é implementado da seguinte forma:

```
            ┌──────── comando de volta: alerta de trecho crítico / troca de trecho ◄───────┐
            ▼                                                                              │
 Entradas        ESP32               Broker MQTT        Receptor              Banco        │
 VL53L0X  ─►  lógica embarcada  ─►   HiveMQ       ─►   Python          ─►    SQLite  ──────┘
 DHT22         Wi-Fi                 público            regras + alertas      compartilhado
 botão           │                                          │                    │
                 ▼                                          ▼                    ▼
               LEDs                                      Alertas            Agente GenAI
            ação local                             console / Telegram     consulta o banco
```
Figura 2. Fluxo do módulo IoT, incluindo o caminho de volta (servidor → ESP32).

## 3.1 Hardware e origem dos dados

| Componente | Interface | Dado produzido | Uso na solução |
|---|---|---|---|
| VL53L0X (sensor de distância por tempo de voo) | I2C | Distância até o solo, em mm, ~20 vezes por segundo | Profundidade = distância − altura de referência. Classifica a irregularidade em leve ou grave. |
| DHT22 | Digital (1 fio) | Temperatura (°C) e umidade relativa (%) a cada 5 s | Umidade ≥ 85% indica pista molhada. A chuva agrava buracos e aumenta a prioridade do trecho. |
| Botão | GPIO com pull-up | Clique (reporte manual) | O motorista ou agente confirma um buraco que viu ou sentiu. |
| 3 LEDs (verde, amarelo, vermelho) | GPIO | não se aplica | Ação local: estado da via e alerta de trecho crítico enviado pelo servidor. |
| Trecho da via (GPS simulado) | Comando MQTT ou Serial | Código do trecho atual | Associa cada leitura a uma rua. No protótipo é informado por `iot/definir_trecho.py` ou pelo Serial Monitor. |

## 3.2 Ligações (ESP32 DevKit)

| Componente | Ligação |
|---|---|
| VL53L0X | VIN → 3V3 · GND → GND · SDA → GPIO 21 · SCL → GPIO 22 |
| DHT22 | VCC → 3V3 · DATA → GPIO 4 (resistor de 10 kΩ para 3V3, se o módulo não tiver) · GND → GND |
| Botão | um terminal → GPIO 13, outro → GND (pull-up interno) |
| LED verde / amarelo / vermelho | GPIO 25 / 26 / 33 → resistor de 220 Ω → LED → GND |

## 3.3 Firmware e lógica embarcada

O firmware é um projeto **PlatformIO** (`iot/esp32_citizentech/`: `platformio.ini` e `src/main.cpp`), com plataforma espressif32 6.12 (núcleo Arduino-ESP32 2.0.17) e as bibliotecas PubSubClient, VL53L0X (Pololu), DHT sensor library e Adafruit Unified Sensor, baixadas automaticamente pelo `platformio.ini`. As credenciais do Wi-Fi ficam em `include/credenciais.h`, fora do controle de versão.

- **Calibração:** ao ligar, ou por comando, o ESP32 faz 30 leituras sobre superfície plana e usa a média como altura de referência.
- **Leitura do sensor de distância:** o VL53L0X opera em modo contínuo (orçamento de 33 ms por medida) e cada valor passa por um **filtro de mediana de 3 amostras**, que elimina picos isolados de ruído sem atrasar a detecção.
- **Detecção:** uma irregularidade começa quando a profundidade passa de 15 mm em pelo menos 2 leituras seguidas. Ela termina quando a profundidade volta abaixo de 10 mm (histerese de 5 mm). Nesse momento é publicado um único evento por passagem, com a profundidade máxima: leve abaixo de 40 mm, grave a partir de 40 mm. Os limiares estão em escala de maquete e são configuráveis no código.
- **Telemetria:** a cada 5 s é publicada uma leitura com distância, profundidade, temperatura, umidade, indicação de pista úmida, status (ok / leve / grave) e a **saúde dos sensores** (`vl_ok`, `dht_ok`), além da altura calibrada e do sinal do Wi-Fi.
- **Robustez com o hardware real:** se o VL53L0X deixa de responder (20 timeouts seguidos) o firmware tenta reconectá-lo a cada 5 s e recalibra; leituras inválidas do DHT22 mantêm o último valor válido e, após 3 falhas, o sensor é marcado como indisponível. O receptor avisa a equipe quando um sensor falha.
- **Fila de eventos:** se o MQTT cair (veículo sem sinal), até 12 eventos ficam guardados na memória e são reenviados na reconexão.
- **Botão:** debounce de 50 ms; cada clique gera um evento `reporte_manual`.
- **LEDs:** verde = via ok; amarelo = irregularidade leve ou pista úmida; vermelho = buraco grave; vermelho piscando por 5 s = trecho crítico (comando do servidor); os três acesos por um instante = troca de trecho ou botão confirmados.
- **GPS simulado:** o ESP32 liga no trecho SIM0001. Ao mover o carrinho para outra "rua" da maquete, o operador envia o código do trecho pelo computador (`definir_trecho.py`) ou digita `trecho SIM0002` no Serial Monitor.
- **Comandos pelo Serial Monitor:** `trecho <código>`, `calibrar`, `status` (diagnóstico de Wi-Fi, MQTT e sensores) e `reporte`.

# 4. Comunicação MQTT

O dispositivo usa o broker público `broker.hivemq.com:1883` e a biblioteca PubSubClient, com buffer ampliado para 512 bytes por causa do tamanho do JSON. Todos os tópicos seguem o padrão `<base>/<device_id>/<tipo>`, com base `fiap/citizentech/gohorse-gs2026` (única do grupo, pois o broker é compartilhado). O receptor assina `fiap/citizentech/gohorse-gs2026/+/+` e trata todos os dispositivos de uma vez.

| Tópico | Direção | Conteúdo |
|---|---|---|
| `…/leitura` | ESP32 → servidor | Telemetria periódica (a cada 5 s) |
| `…/evento` | ESP32 → servidor | `buraco` (leve/grave), `reporte_manual`, `mudanca_trecho`, `calibracao`, `alerta_recebido`, `online` |
| `…/status` | ESP32 → servidor | `online` / `offline`, retido. O `offline` é publicado pelo broker via Last Will quando o ESP32 cai. |
| `…/comando` | servidor → ESP32 | `{"acao":"alerta"}`, `{"acao":"trecho","codigo":"SIM0002"}`, `{"acao":"calibrar"}`, `{"acao":"ping"}` |

Exemplos de payload (JSON):
```
leitura: {"device":"esp32-01","trecho":"SIM0002","dist_mm":208,"prof_mm":58,
          "temp_c":27.2,"umid":62.8,"pista_umida":false,"status":"grave",
          "vl_ok":true,"dht_ok":true,"base_mm":150,"rssi":-58,"ts":1794864941}
evento:  {"device":"esp32-01","tipo":"buraco","severidade":"grave","trecho":"SIM0002",
          "prof_mm":63,"temp_c":27.0,"umid":62.0,"ts":1794864942}
comando: {"acao":"alerta","motivo":"trecho crítico: Av. Lins de Vasconcelos, 800-1200",
          "pontuacao":9.0}
```

# 5. Armazenamento e uso dos dados

O receptor (`iot/receptor_mqtt.py`) grava cada mensagem num banco SQLite (`citizentech.db`). Esse mesmo banco é usado pelos módulos de Visão e de GenAI: é por ele que os dados dos sensores chegam ao agente de IA generativa.

| Tabela / view | Quem grava | Conteúdo |
|---|---|---|
| `trechos` | cadastro | Código do trecho → nome da via, bairro e coordenadas |
| `leituras_iot` | receptor | Telemetria periódica do ESP32 |
| `eventos_iot` | receptor | Buracos, reportes, trocas de trecho, calibrações |
| `deteccoes_visao` | módulo de Visão | Classe, confiança e caixa de cada detecção do YOLO |
| `status_dispositivos` | receptor | Online / offline de cada ESP32 |
| `vw_prioridade_trechos` | (view) | Pontuação e nível de prioridade de cada trecho. É a fonte principal do agente GenAI. |

> Pontuação do trecho = (3 × buracos graves + 1 × irregularidades leves + 2 × reportes manuais + 2 × detecções visuais com confiança ≥ 0,5) × 1,2 se a umidade média for ≥ 80%. Nível: alta ≥ 8 · média ≥ 4 · baixa > 0.

**Regras que transformam dados em informação, alerta ou ação**

| Condição | Resposta da solução |
|---|---|
| Evento de buraco grave | Alerta no console e no Telegram: "Buraco GRAVE em <trecho>… Vistoria recomendada" |
| Reporte manual (botão) | Alerta com o trecho e a condição climática |
| Trecho passa a prioridade alta | Alerta para a zeladoria com o resumo das evidências (graves, leves, reportes, detecções visuais) |
| Veículo entra em trecho de prioridade alta | O servidor publica um comando `alerta`; o ESP32 pisca o LED vermelho ("trecho crítico à frente") |
| Umidade ≥ 85% | LED amarelo no dispositivo e peso 1,2 na pontuação do trecho |
| Sensor sem leitura (`vl_ok`/`dht_ok` falso) | Alerta "Sensor sem leitura no <dispositivo>… Verifique as ligações" |
| Consulta pelo agente GenAI | Relatório de inspeção com ranking explicado e rota sugerida; alerta ao veículo quando o trecho mais crítico está em nível alta |

# 6. Testes e evidências de funcionamento

## 6.1 Metodologia

- **Firmware:** compilado com sucesso pelo PlatformIO para a placa ESP32 Dev Module (sem avisos do compilador), usando 15,2% da RAM e 60,5% da memória de programa.
- **Fluxo ponta a ponta com simulador:** broker MQTT local, receptor e um simulador do ESP32 (`iot/simulador_esp32.py`) que publica os mesmos tópicos e payloads do firmware. Foram trocadas 14 leituras e 12 eventos, todos gravados no banco (seções 6.2 a 6.4).
- **Fluxo pelo broker público:** mensagens no formato exato do firmware (incluindo `vl_ok`/`dht_ok`) publicadas em `broker.hivemq.com` foram recebidas pelo receptor, gravadas no banco e geraram os alertas esperados, inclusive o de sensor sem leitura.
- **Protótipo físico:** ESP32 real com os sensores na maquete, testado em 19/11/2026 (situações 1, 2 e 4). Resultados, fotos e vídeo na seção 6.5.

## 6.2 Situações de entrada testadas (simulador)

| # | Entrada | Mensagem MQTT | Efeito observado |
|---|---|---|---|
| 1 | Pista plana, umidade 58% | `leitura` com status "ok" | LED verde; leituras gravadas |
| 2 | Rebaixos de 22 mm, 58 mm e 63 mm | evento `buraco` leve e 2 eventos `buraco` grave | LED amarelo/vermelho; 2 alertas "Buraco GRAVE… Vistoria recomendada" |
| 3 | Chuva: umidade 92% e rebaixos de 18 e 27 mm | leituras com `pista_umida = true`; 2 eventos leves | LED amarelo; pontuação do trecho multiplicada por 1,2 (2,4) |
| 4 | Botão pressionado na Av. Lins | evento `reporte_manual` | Alerta de reporte; trecho passa a prioridade ALTA (9,0) e a zeladoria é avisada |
| 5 | Veículo volta ao trecho crítico | `mudanca_trecho` → servidor publica comando `alerta` | ESP32 recebe o comando e pisca o LED vermelho; confirma com `alerta_recebido` |

## 6.3 Registro do receptor (execução simulada)

```
LOG_RECEPTOR
```
Trecho integral do log do receptor; o arquivo completo está em `iot/evidencias/`.

## 6.4 Resultado gravado no banco

| Trecho | Graves | Leves | Reportes | Visão | Prof. máx. | Umid. média | Pontos | Nível |
|---|---|---|---|---|---|---|---|---|
| Av. Lins de Vasconcelos, 800-1200 | 2 | 1 | 1 | 0 | 63 mm | 62,5% | 9,0 | alta |
| Rua Domingos de Morais, 2000-2400 | 0 | 2 | 0 | 0 | 27 mm | 92,0% | 2,4 | baixa |
| Rua Vergueiro, 1000-1400 | 0 | 0 | 0 | 0 | n/d | 58,0% | 0,0 | sem registro |
| Av. Jabaquara, 500-900 | 0 | 0 | 0 | 0 | n/d | n/d | 0,0 | sem registro |

A Av. Lins de Vasconcelos reuniu dois buracos graves, uma irregularidade leve e um reporte manual, e ficou com prioridade alta. A Rua Domingos de Morais teve só irregularidades leves, mas sob chuva, o que elevou sua pontuação de 2,0 para 2,4. A Rua Vergueiro teve apenas leituras normais e não entrou no ranking. A Av. Jabaquara não foi percorrida no teste.

## 6.5 Evidências do protótipo físico

EVIDENCIAS_FISICAS

# 7. Implementado, simulado e limitações

| Situação | Itens |
|---|---|
| Implementado | Firmware PlatformIO completo para os sensores reais (VL53L0X com filtro de mediana e reconexão, DHT22, botão, LEDs, MQTT nos dois sentidos, Last Will, fila de eventos offline, comandos pelo Serial), receptor com gravação em banco, regras de prioridade, alertas no console e no Telegram, aviso de sensor com falha, comando de volta ao dispositivo, simulador e scripts de consulta. |
| Simulado | Localização por GPS simulado (trecho informado por comando MQTT ou Serial). Buracos representados por rebaixos numa maquete, com limiares em escala reduzida. Trechos SIM0001 a SIM0004 e coordenadas fictícios. |
| Validação | Firmware compilado e gravado no ESP32 real. Teste no hardware em 19/11/2026 com as situações 1, 2 e 4 (seção 6.5). Situações 3 e 5 validadas com o simulador e com payloads do firmware pelo broker público. |

| Limitação | Impacto | Mitigação / evolução |
|---|---|---|
| VL53L0X sensível a luz solar direta e a superfícies escuras ou molhadas | Leituras ruidosas ao ar livre | Filtro de mediana já aplicado; sensor com proteção óptica ou LiDAR automotivo |
| Vibração e suspensão de um veículo real | Falsos positivos | Acelerômetro (MPU6050) e fusão de sensores |
| DHT22 mede o ar, não o pavimento | Indicador indireto de chuva | Sensor de chuva ou dados meteorológicos abertos |
| Sem GPS real | Localização manual na demo | Módulo GPS (ex.: NEO-6M) para coordenadas automáticas |
| Broker público sem autenticação | Qualquer um pode ler ou publicar nos tópicos | Broker próprio com TLS, usuário/senha e ACL por dispositivo |
| Fila de eventos só na RAM | Eventos perdidos se o ESP32 reiniciar sem sinal | Gravar a fila na flash (LittleFS) |
| Sensor levantado ou inclinado | Profundidades irreais (469 e 532 mm no teste físico) | Descartar leituras acima de uma profundidade máxima plausível |
| Pontuação heurística | Pesos definidos pelo grupo, não calibrados com dados reais | Ajustar os pesos com o histórico de vistorias |

> **Uso responsável:** a solução faz triagem e ajuda a priorizar rotas de inspeção. Uma detecção automática não substitui a vistoria técnica presencial, que continua necessária para atestar a gravidade real e decidir o reparo.

# 8. Relação com os Objetivos de Desenvolvimento Sustentável

| ODS | Contribuição do projeto |
|---|---|
| ODS 11: Cidades e comunidades sustentáveis (metas 11.2 e 11.7) | Vias mais seguras e acessíveis para todos, inclusive pedestres, ciclistas e usuários de transporte público, com manutenção orientada por dados. |
| ODS 9: Indústria, inovação e infraestrutura (meta 9.1) | Monitoramento contínuo e de baixo custo da infraestrutura viária, ajudando a mantê-la resiliente e de qualidade. |
| ODS 3: Saúde e bem-estar (meta 3.6) | Redução de acidentes de trânsito causados por buracos, especialmente envolvendo motociclistas e ciclistas. |

# 9. Referências

[1] BNews SP. Mesmo após recapeamento, SP registra quase 52 mil pedidos de tapa-buraco. 09/08/2026. Dados da Secretaria Municipal das Subprefeituras. https://www.bnewssaopaulo.com.br/noticias/politica/mesmo-apos-recapeamento-sp-registra-quase-52-mil-pedidos-de-tapa-buraco.html

[2] Prefeitura de São José dos Campos. Chuva em setembro aumenta em 30% o serviço de tapa-buracos. 25/09/2026. https://www.sjc.sp.gov.br/noticias/2026/setembro/24/chuva-em-setembro-aumenta-em-30-o-servico-de-tapa-buracos/

[3] Agência iNFRA. Pesquisa CNT de Rodovias 2026. 09/11/2026. https://agenciainfra.com/blog/?p=49892

[4] Portal do Trânsito. Saiba como solicitar reparação quando o seu veículo sofrer danos causados por buracos em via pública. https://www.portaldotransito.com.br/noticias/mobilidade-e-tecnologia/mobilidade-urbana/saiba-como-solicitar-reparacao-quando-o-seu-veiculo-sofrer-danos-causados-por-buracos-em-via-publica/

# Apêndice A. Código-fonte

Estrutura: `citizentech/` → `config.py`, `banco.py`, `requirements.txt` e a pasta `iot/` com o firmware PlatformIO (`esp32_citizentech/`), o receptor, o simulador, `definir_trecho.py` e `evidencias/`.

CODIGO_FONTE
