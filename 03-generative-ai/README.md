# CitizenTech · Monitor de Pavimento

**Global Solution 2026.2 · FIAP**. Protótipo integrado CitizenTech com IA para apoiar o cidadão.
Tema do grupo: **detecção e priorização de buracos nas vias urbanas**, em três disciplinas que
compartilham o mesmo problema, público e banco de dados.

| Disciplina | Módulo | Entregáveis |
|---|---|---|
| **IoT (Sensores)** | ESP32 com VL53L0X (profundidade), DHT22 (umidade/temperatura), botão e LEDs → MQTT → receptor → banco | `CitizenTech_Modulo_IoT.pdf` · `citizentech/iot/` (firmware PlatformIO em `iot/esp32_citizentech/src/main.cpp`) |
| **Visão Computacional** | YOLO11n ajustado (transfer learning) para detectar buracos em fotos e vídeos, com confiança, latência/FPS e integração ao banco | `CitizenTech_Modulo_Visao.pdf` · `citizentech/visao/visao_computacional.ipynb` |
| **Generative AI and Advanced Nets** | Agente (LangChain + LLM open source **Qwen3-1.7B** do Hugging Face, rodando localmente, sem chave de API) com 9 ferramentas e RAG: relatório de inspeção para a zeladoria, assistente do cidadão, ações no banco, no detector e no ESP32 | `CitizenTech_Modulo_GenAI.pdf` · `citizentech/genai/genai_agente.ipynb` · `citizentech/genai/app_gradio.py` |

```
 VL53L0X ─┐                                        ┌──> alertas (console / Telegram)
 DHT22   ─┼─> ESP32 ──MQTT──> receptor_mqtt.py ──> citizentech.db ──> agente GenAI ──> Gradio (zeladoria / cidadão)
 Botão   ─┘    ▲                                     ▲        ▲               │
 LEDs        ◄─┴───── comando "alerta" ◄─────────────┼────────┼───────────────┘
                                   detector.py (YOLO11n) ─────┘        foto do cidadão ──> detector ──> banco
                                   fotos e vídeo da via (midia/)
```

**Pontuação de prioridade por trecho** (`vw_prioridade_trechos`): `(3×graves + 1×leves + 2×reportes + 2×detecções visuais com confiança ≥ 0,5) × 1,2 se umidade média ≥ 80 %`. Alta ≥ 8 · média ≥ 4 · baixa > 0. É uma heurística de **triagem**: a vistoria presencial continua obrigatória.

## Estrutura

```
citizentech/
├── config.py, banco.py            # MQTT, SQLite compartilhado (tabelas + view de prioridade)
├── iot/                           # firmware ESP32 (PlatformIO: esp32_citizentech/src/main.cpp), receptor MQTT, simulador, evidências
├── visao/                         # preparar_dados.py, treinar.py, detector.py, processar_video.py, notebook, evidencias/, modelos/best.pt
├── genai/                         # agente.py, llm_local.py, ferramentas.py, rag.py, app_gradio.py, avaliacao.py, base_conhecimento/, notebook
└── relatorios/                    # fontes Markdown dos PDFs + gerar_relatorios.py
midia/                             # fotos e cortes curtos da rua (o vídeo bruto pode ficar na raiz; fica fora do Git)
ROTEIRO_VIDEO.md                   # roteiro da demonstração em vídeo
```

## Como rodar

```bash
python -m venv .venv && .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements.txt
```

**IoT** (detalhes em `citizentech/README.md`)
```bash
.venv/bin/python citizentech/iot/receptor_mqtt.py            # terminal 1: assina o broker e grava no banco
.venv/bin/python citizentech/iot/simulador_esp32.py --cenario demo   # terminal 2 (ou o ESP32 físico)
cd citizentech/iot/esp32_citizentech && ../../../.venv/bin/pio run -t upload   # gravar o firmware no ESP32
.venv/bin/python citizentech/banco.py --resumo                # ranking de prioridade
```

**Visão computacional**
```bash
.venv/bin/python citizentech/visao/preparar_dados.py          # baixa 2 bases públicas, divide por foto de origem
.venv/bin/python citizentech/visao/treinar.py --epochs 30     # ~100 min em CPU (Core 7 240H) → modelos/best.pt
.venv/bin/python citizentech/visao/processar_video.py --video rua.mp4 --trecho SIM0005 --gravar-banco   # vídeo na raiz
.venv/bin/jupyter notebook citizentech/visao/visao_computacional.ipynb
```

**GenAI**
```bash
# sem chave de API: o Qwen3-1.7B (~3,4 GB) é baixado do Hugging Face na 1ª execução e roda na CPU
.venv/bin/python citizentech/genai/rag.py --reconstruir       # índice FAISS da base de conhecimento
.venv/bin/python citizentech/genai/app_gradio.py              # http://localhost:7860
.venv/bin/python citizentech/genai/agente.py --relatorio      # relatório de inspeção no terminal
.venv/bin/python citizentech/genai/avaliacao.py               # 12 cenários + juiz (~15-25 min em CPU) → evidencias/
```

**Relatórios em PDF** (após executar os notebooks): `.venv/bin/python citizentech/relatorios/gerar_relatorios.py` (os três; ou `iot`, `visao`, `genai`). Nomes e RMs da capa: `citizentech/relatorios/_md_para_pdf.py`.

## Evidências
- IoT: `citizentech/iot/evidencias/` (logs do receptor e do simulador, ranking, últimos eventos) + fotos/prints do protótipo físico em `iot/evidencias/fisico/` (entram na seção 6.5 do PDF).
- Visão: `citizentech/visao/evidencias/` (figuras do notebook, `metricas_visao.json`) e `citizentech/visao/saida/` (vídeos anotados).
- GenAI: `citizentech/genai/evidencias/` (resultados da avaliação, fotos analisadas) e as saídas do notebook.

## ODS
ODS 11 (metas 11.2 e 11.7), ODS 9 (meta 9.1) e ODS 3 (meta 3.6).

## Integrantes
| Nome completo | RM |
|---|---|
| Leonardo Barros | 566788 |
| Marcelo Augusto | 567176 |
| Yuri Quirino | 568512 |
