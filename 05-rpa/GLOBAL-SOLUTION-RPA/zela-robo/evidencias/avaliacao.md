# Avaliação da IA de triagem

- Treino: 880 relatos sintéticos gerados por combinação de frases (`dados/treino.csv`).
- Teste: 132 relatos escritos à mão, 11 categorias (`dados/teste_rotulado.csv`). Relatos do teste que também estão no treino: 0.
- Modelo: TF-IDF (palavras e pedaços de palavra) + regressão logística, scikit-learn.

## Resultado geral

| Classificador | Acertos | Acurácia |
| --- | --- | --- |
| Modelo de ML (robô) | 104 de 132 | 78.8% |
| Regras do aplicativo (referência) | 69 de 132 | 52.3% |

## Efeito do limiar de confiança (em uso: 50%)

Abaixo do limiar, ou quando a categoria é "outros", o pedido vai para revisão humana.

| Limiar   |   Encaminhados sozinho | % automatizado   |   Encaminhados certo |   Encaminhados errado | Acerto no automático   |   Para revisão humana |
|:---------|-----------------------:|:-----------------|---------------------:|----------------------:|:-----------------------|----------------------:|
| 0%       |                    118 | 89%              |                   94 |                    24 | 79.7%                  |                    14 |
| 30%      |                    103 | 78%              |                   88 |                    15 | 85.4%                  |                    29 |
| 40%      |                     91 | 69%              |                   84 |                     7 | 92.3%                  |                    41 |
| 45%      |                     85 | 64%              |                   79 |                     6 | 92.9%                  |                    47 |
| 50%      |                     80 | 61%              |                   77 |                     3 | 96.2%                  |                    52 |
| 60%      |                     64 | 48%              |                   63 |                     1 | 98.4%                  |                    68 |
| 70%      |                     52 | 39%              |                   52 |                     0 | 100.0%                 |                    80 |

Com o limiar de 50%: o robô encaminha sozinho 80 de 132 pedidos (61%), acerta 77 e erra 3; 52 vão para uma pessoa.

## Precisão e recall por categoria (sem limiar)

```
                precision    recall  f1-score   support

acessibilidade       0.79      0.92      0.85        12
          agua       0.75      1.00      0.86        12
       arvores       0.82      0.75      0.78        12
       barulho       0.90      0.75      0.82        12
    iluminacao       0.91      0.83      0.87        12
        outros       0.71      0.83      0.77        12
      residuos       0.88      0.58      0.70        12
         saude       0.58      0.58      0.58        12
      transito       0.92      0.92      0.92        12
    transporte       1.00      0.67      0.80        12
          vias       0.62      0.83      0.71        12

      accuracy                           0.79       132
     macro avg       0.81      0.79      0.79       132
  weighted avg       0.81      0.79      0.79       132
```

## Matriz de confusão (linha = correto, coluna = previsto)

|                |   iluminacao |   vias |   residuos |   agua |   arvores |   transito |   transporte |   saude |   acessibilidade |   barulho |   outros |
|:---------------|-------------:|-------:|-----------:|-------:|----------:|-----------:|-------------:|--------:|-----------------:|----------:|---------:|
| iluminacao     |           10 |      1 |          0 |      0 |         1 |          0 |            0 |       0 |                0 |         0 |        0 |
| vias           |            0 |     10 |          0 |      0 |         1 |          0 |            0 |       1 |                0 |         0 |        0 |
| residuos       |            0 |      2 |          7 |      1 |         0 |          0 |            0 |       0 |                0 |         0 |        2 |
| agua           |            0 |      0 |          0 |     12 |         0 |          0 |            0 |       0 |                0 |         0 |        0 |
| arvores        |            0 |      1 |          0 |      0 |         9 |          1 |            0 |       0 |                1 |         0 |        0 |
| transito       |            0 |      0 |          0 |      0 |         0 |         11 |            0 |       0 |                0 |         1 |        0 |
| transporte     |            0 |      0 |          0 |      1 |         0 |          0 |            8 |       2 |                1 |         0 |        0 |
| saude          |            0 |      1 |          1 |      2 |         0 |          0 |            0 |       7 |                0 |         0 |        1 |
| acessibilidade |            0 |      1 |          0 |      0 |         0 |          0 |            0 |       0 |               11 |         0 |        0 |
| barulho        |            1 |      0 |          0 |      0 |         0 |          0 |            0 |       1 |                0 |         9 |        1 |
| outros         |            0 |      0 |          0 |      0 |         0 |          0 |            0 |       1 |                1 |         0 |       10 |

## Erros (28)

Lista completa em `avaliacao_erros.csv`.

| relato                                                                       | correto        | previsto       |   confianca |
|:-----------------------------------------------------------------------------|:---------------|:---------------|------------:|
| Queria saber quando passa o cata-treco, tenho um guarda-roupa pra descartar  | residuos       | outros         |        0.69 |
| Pneus velhos acumulando agua da chuva no ferro velho, nuvem de pernilongo    | saude          | agua           |        0.66 |
| Vizinho acumula lixo e bicho dentro de casa, ta juntando rato                | saude          | residuos       |        0.57 |
| Tem vaga na escola municipal para o ano que vem?                             | outros         | acessibilidade |        0.51 |
| Matagal tomou conta do terreno da prefeitura, ta mais alto que o muro        | residuos       | outros         |        0.48 |
| Coqueiro com frutos caindo em cima dos carros estacionados                   | arvores        | transito       |        0.46 |
| O elevador do onibus para cadeirante nunca funciona                          | transporte     | acessibilidade |        0.46 |
| Geladeira velha e armario largados na beira do corrego                       | residuos       | agua           |        0.46 |
| O imovel abandonado esta infestado de baratas que invadem as casas           | saude          | agua           |        0.41 |
| Tem um cavalo solto e doente andando pela avenida                            | saude          | vias           |        0.37 |
| Raizes levantaram o piso e estouraram o muro                                 | arvores        | acessibilidade |        0.36 |
| O abrigo do ponto esta sem telhado, a gente toma chuva esperando             | transporte     | agua           |        0.35 |
| Ar condicionado do coletivo quebrado, um calor infernal la dentro            | transporte     | saude          |        0.33 |
| Alguém despejou restos de construção na calçada e bloqueou a passagem        | residuos       | vias           |        0.33 |
| Gostaria de pedir o plantio de mudas na calçada da escola                    | arvores        | vias           |        0.32 |
| Cabo de energia arrebentou e ficou pendurado na altura da cabeça das pessoas | iluminacao     | arvores        |        0.31 |
| Depois da feira a rua fica imunda e ninguém limpa                            | residuos       | vias           |        0.31 |
| A fabrica ao lado tem uma maquina que apita a noite toda                     | barulho        | iluminacao     |        0.3  |
| A plataforma elevatória do posto de saude esta quebrada desde janeiro        | acessibilidade | vias           |        0.28 |
| A rua inteira ta um breu depois das 18h, nenhuma lampada acende              | iluminacao     | vias           |        0.27 |
| Cachorro do vizinho late a noite inteira, ja pedi e ele nao faz nada         | barulho        | outros         |        0.26 |
| Pedimos um radar ou fiscalizacao, tem racha de moto toda noite na avenida    | transito       | barulho        |        0.22 |
| Tem uma vala aberta de lado a lado na rua, obra abandonada                   | vias           | arvores        |        0.18 |
| O vizinho liga a serra eletrica as 6 da manha de domingo                     | barulho        | saude          |        0.18 |
| A estação está com a escada rolante parada há meses                          | transporte     | saude          |        0.17 |
| Caramujos enormes subindo pelo muro da horta comunitaria                     | saude          | outros         |        0.16 |
| Faz anos que pedimos pavimentação dessa travessa e nada                      | vias           | saude          |        0.16 |
| Qual o telefone da ouvidoria?                                                | outros         | saude          |        0.14 |
