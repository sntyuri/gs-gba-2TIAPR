# Zeladoria urbana com IA: Global Solution 2026.2

FIAP, Tecnologia em Inteligência Artificial, turma 2TIAPR. Tema: CitizenTech.

Este repositório reúne todas as entregas do grupo na Global Solution 2026.2, uma pasta por disciplina.

## Integrantes

| Nome | RM |
|---|---|
| Yuri Quirino | 568512 |
| Leonardo Barros | 566788 |
| Marcelo Augusto | 567176 |

## Entrega de Governança

- Documento de integração (PDF): `09-governanca/governanca-gs-2026-2-2tiapr.pdf`
- Vídeo de demonstração da integração: https://youtu.be/25fgZ2l0W2o

## Pastas

| Pasta | Disciplina | Responsável | Frente |
|---|---|---|---|
| `01-iot` | Physical Computing, Embedded AI, Robotics & Cognitive IoT | Leonardo | Monitor de Pavimento |
| `02-visao-computacional` | Visão Computacional | Leonardo | Monitor de Pavimento |
| `03-generative-ai` | Generative AI and Advanced Nets | Leonardo | Monitor de Pavimento |
| `04-front-end` | Front End & Mobile Development | Grupo | Zela |
| `05-rpa` | AI for Robotic Process Automation | Marcelo | Zela |
| `06-fabrica-de-corpus` | Fábrica de Corpus (PLN) | Marcelo | Não integrada |
| `07-neuromorfica` | Cluster Computing, Computação Neuromórfica e Supercomputadores | Yuri | Estudo sobre o Monitor |
| `08-quantica` | Computação Quântica | Yuri | Estudo sobre o Monitor |
| `09-governanca` | Governança em IA e Business Analytics | Yuri | Integração |

## O que está integrado

- **Monitor de Pavimento:** o sensor (IoT), o detector de buracos (Visão) e o agente (IA generativa) leem e gravam no mesmo banco SQLite.
- **Zela:** o aplicativo exporta os pedidos em JSON e o robô de RPA devolve as respostas em outro arquivo. A troca dos arquivos é manual.
- **Sem ligação:** um buraco detectado pelo Monitor não vira pedido no Zela, e a Fábrica de Corpus trata de outro tema (dengue e vacinação).
- **Simulação:** Neuromórfica e Quântica são estudos sobre o Monitor, sem código em produção.

A matriz completa do que foi e do que não foi integrado está na seção 2.9 do documento de Governança.

## Outros vídeos

- Front End: https://www.youtube.com/watch?v=AWBrr_YskyI
- RPA: https://youtu.be/-C7ik9AzzbY
- Fábrica de Corpus: https://youtu.be/7gRQgno7nmk
- IoT: arquivo na pasta `01-iot`
- Visão Computacional e IA generativa: entregues ao professor em arquivo separado
