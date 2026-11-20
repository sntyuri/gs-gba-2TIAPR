# Fábrica de Corpus CitizenTech: Dengue e vacinação no SUS

Global Solution 2027 · FIAP · Tecnólogo em Inteligência Artificial

Ferramenta em Python (Google Colab + Gradio) que transforma documentos públicos de saúde em **três corpus prontos para o fine-tuning de um modelo de linguagem pequeno (SLM)**. O modelo treinado com esses dados atenderia cidadãos com dúvidas sobre dengue e vacinação, em linguagem simples e sem enviar dados para a nuvem.

**ODS apoiado:** ODS 3 – Saúde e Bem-Estar.

## Integrantes

| Nome | RM |
|------|----|
| Yuri Quirino | 568512 |
| Leonardo Barros | 566788 |
| Marcelo Augusto | 567176 |

## Estrutura do repositório

```
├── fabrica_corpus_citizentech.ipynb   # notebook com a ferramenta completa
├── README.md
├── relatorio_GS_fabrica_de_corpus.pdf # relatório (até 6 páginas)
├── documentos/                        # documentos de entrada usados
│   ├── originais/                     # arquivos como foram baixados das fontes oficiais
│   └── entrada_final/                 # arquivos enviados à ferramenta na execução final
└── corpus/                            # saídas da ferramenta
    ├── corpus_texto.jsonl
    ├── corpus_qa.jsonl
    ├── corpus_chat.jsonl
    ├── relatorio_qualidade.md
    ├── estatisticas.json
    └── registro_revisao.csv
```

## Como executar

### 1. Abrir o notebook
1. Acesse o [Google Colab](https://colab.research.google.com) e abra `fabrica_corpus_citizentech.ipynb` (menu **Arquivo > Fazer upload de notebook**, ou direto pelo GitHub).
2. Não é preciso GPU: o ambiente padrão de CPU é suficiente.

### 2. (Opcional) Configurar a chave do Gemini
A chave é usada para gerar as perguntas e os diálogos com IA. **Sem ela, a ferramenta funciona normalmente** e gera esses exemplos por regras, a partir de frases dos próprios documentos.

1. Crie uma chave gratuita no [Google AI Studio](https://aistudio.google.com) (**Get API key**).
2. No Colab, abra o painel **Secrets** (ícone de chave 🔑 na barra lateral esquerda).
3. Clique em **Add new secret**, use o nome `GEMINI_API_KEY` e cole a chave em **Value**.
4. Ative o botão **Notebook access** dessa linha.

### 3. Executar todas as células
Use **Ambiente de execução > Executar tudo** (*Runtime > Run all*). O notebook:

1. instala as bibliotecas (seção 0);
2. carrega todas as etapas do pipeline (seções 1 a 9);
3. testa a chave do Gemini e mostra o modelo usado, ou o motivo de a chave não ter sido encontrada (seção 7, célula **Teste da chave**);
4. baixa os documentos oficiais sugeridos para a pasta `documentos_entrada/` (seção 10);
5. abre a interface Gradio (seção 11), com um link público `*.gradio.live`.

> Se o Colab pedir para reiniciar a sessão depois da instalação, aceite e execute tudo de novo.

### 4. Usar a interface Gradio
A interface tem uma aba para cada etapa:

| Aba | O que fazer ou ver |
|---|---|
| **1. Entrada** | Envie de 3 a 5 documentos (PDF, TXT, DOCX ou HTML), cole um texto se quiser e clique em **Executar pipeline**. |
| **2. Extração e origem** | Arquivo e página de onde veio cada bloco de texto. |
| **3. Limpeza e normalização** | Antes e depois de cada documento. |
| **4. Anonimização** | Quantidade de CPFs, e-mails, telefones e nomes mascarados, com exemplos de antes e depois. |
| **5. Corpus** | Download dos arquivos gerados e prévia dos três corpus. |
| **6. Relatório de qualidade** | Estatísticas, duplicatas removidas e 5 exemplos aleatórios de cada corpus. |
| **7. Revisão humana** | Amostra de 20% dos exemplos gerados. Edite ou desmarque **manter** e clique em **Aplicar revisão**. |

Para usar os documentos baixados pela seção 10, faça o download deles da pasta `documentos_entrada/` (painel **Arquivos** do Colab) e envie-os na aba 1.

Com a IA ativada, a geração leva alguns minutos, porque a ferramenta respeita o limite de requisições da camada gratuita do Gemini.

### 5. Baixar os resultados
Depois de aplicar a revisão, baixe os arquivos pela aba **5. Corpus** ou pela pasta `saida/` do Colab. **A pasta `saida/` é apagada quando a sessão do Colab termina** e é regravada a cada nova execução.

### Execução sem interface (opcional)
A seção 12 gera os corpus direto pelas células, usando os arquivos de `documentos_entrada/`. Ela vem desligada: troque `RODAR_SEM_INTERFACE = False` para `True` e execute a célula.

## Pipeline

1. **Ingestão:** PDF, TXT, DOCX, HTML e texto colado.
2. **Extração:** texto de cada arquivo, com registro de origem (arquivo e página).
3. **Limpeza:** remove cabeçalhos, rodapés, números de página, sumário, URLs, caracteres estranhos, linhas repetidas, créditos e referências bibliográficas; une palavras hifenizadas.
4. **Normalização:** codificação UTF-8 (NFC), espaços, quebras de linha e aspas. Acentos, pontuação e maiúsculas são mantidos; não há remoção de *stop words* nem *stemming*.
5. **Anonimização (LGPD):** CPF, e-mail, telefone e nomes de pessoas viram `[CPF]`, `[EMAIL]`, `[TELEFONE]` e `[NOME]`. Telefones de utilidade pública (136, 192, 0800) são mantidos.
6. **Segmentação:** trechos de 256 a 512 tokens, sempre em fim de frase.
7. **Geração dos corpus:** texto puro, perguntas e respostas, e conversacional, mais 14 diálogos manuais de recusa e encaminhamento.
8. **Relatório de qualidade:** estatísticas, duplicatas removidas e amostras.

## Formato dos corpus

**`corpus_texto.jsonl`**
```json
{"text": "trecho do documento...", "fonte": "arquivo_de_origem.pdf"}
```

**`corpus_qa.jsonl`**
```json
{"instruction": "pergunta do cidadão", "input": "", "output": "resposta", "fonte": "arquivo_de_origem.pdf"}
```

**`corpus_chat.jsonl`**
```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], "fonte": "arquivo_de_origem.pdf"}
```

## Fontes utilizadas

| Documento | Órgão | Link |
|---|---|---|
| O Agente Comunitário de Saúde no controle da dengue (PDF) | Ministério da Saúde | [cartilha_acs_dengue_web.pdf](https://mosquito.saude.es.gov.br/Media/dengue/Arquivos/cartilha_acs_dengue_web.pdf) |
| Cartilha de acompanhamento da vacinação pelo ACS (PDF) | Ministério da Saúde | [cartilhadoacs.pdf](https://www.gov.br/saude/pt-br/acesso-a-informacao/participacao-social/consultas-publicas/2023/consulta-publica-cartilha-de-acompanhamento-da-vacinacao-pelo-agente-comunitario-de-saude/cartilhadoacs.pdf) |
| Dengue – Saúde de A a Z (HTML) | Ministério da Saúde | [gov.br/saude/.../dengue](https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dengue) |
| Vacinação (HTML) | Ministério da Saúde | [gov.br/saude/pt-br/vacinacao](https://www.gov.br/saude/pt-br/vacinacao) |
| Calendário Nacional de Vacinação (HTML) | Ministério da Saúde | [gov.br/saude/pt-br/vacinacao/calendario](https://www.gov.br/saude/pt-br/vacinacao/calendario) |

Para demonstrar todos os formatos aceitos, dois documentos foram convertidos sem alterar o conteúdo: a cartilha de vacinação do ACS (PDF → DOCX) e a página de Vacinação (HTML → TXT). Os originais estão em `documentos/originais/`.

## Tecnologias
Python, Google Colab, Gradio, pdfplumber, pypdf, python-docx, BeautifulSoup, ftfy, spaCy (`pt_core_news_sm`), tiktoken e Google Gemini (`google-genai`).

## Links
- **Vídeo de demonstração:** _adicionar link_
- **Relatório:** `relatorio_GS_fabrica_de_corpus.pdf`
