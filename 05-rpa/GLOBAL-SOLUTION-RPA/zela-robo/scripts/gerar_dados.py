"""Gera os dados SINTÉTICOS do protótipo (nenhum dado real de cidadão é usado).

    python scripts/gerar_dados.py

Cria:
  dados/treino.csv                     relatos rotulados para treinar o modelo
  dados/exemplos/balcao_atendimento.xlsx  planilha de exemplo do balcão

Os relatos de treino são montados por combinação de frases (abertura + problema +
local + complemento), com semente fixa para o resultado ser sempre o mesmo.
O conjunto de teste (dados/teste_rotulado.csv) NÃO é gerado aqui: foi escrito à
mão, com outras palavras, para medir o modelo em textos que ele nunca viu.
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
POR_CATEGORIA = 80
SEMENTE = 2026

ABERTURAS = ["", "", "", "Bom dia.", "Boa tarde,", "Olá,", "Oi, tudo bem?", "Boa noite.",
             "Gostaria de registrar uma reclamação:", "Venho pedir ajuda:", "Por favor,",
             "Preciso informar que", "Quero avisar que", "Atenção:"]

LOCAIS = ["", "", "na minha rua", "aqui no bairro", "em frente à minha casa", "perto do mercado",
          "na esquina de casa", "na avenida principal", "perto da escola", "ao lado da padaria",
          "na rua de trás", "perto do posto de saúde", "na praça do bairro", "na frente do prédio",
          "na rua da feira", "perto da igreja", "no fim da rua", "na entrada da vila"]

COMPLEMENTOS = ["", "", "", "Já faz tempo.", "Há duas semanas está assim.", "Ninguém resolve.",
                "Já reclamei e nada foi feito.", "Peço providência.", "Os moradores estão cansados.",
                "Está cada dia pior.", "Aguardo retorno.", "É a terceira vez que aviso.",
                "Faz mais de um mês.", "Todo dia é a mesma coisa.", "Obrigado.", "Favor verificar.",
                "Isso é um perigo.", "Tem criança e idoso passando por aqui."]

PROBLEMAS = {
    "iluminacao": [
        "o poste está com a luz apagada", "a lâmpada do poste queimou", "a rua está sem iluminação à noite",
        "tem um fio solto pendurado no poste", "a luminária fica piscando a noite toda",
        "o poste está aceso de dia e apagado de noite", "a rua fica toda escura porque as luzes não acendem",
        "tem fiação caída soltando faísca", "a luz da rua queimou", "três postes seguidos estão apagados",
        "o poste de luz está inclinado e com os fios baixos", "a iluminação pública não funciona",
        "o refletor da quadra está queimado", "o braço da luminária do poste quebrou",
        "está tudo no escuro, as lâmpadas da rua não acendem", "o poste está dando curto e estalando",
    ],
    "vias": [
        "tem um buraco enorme no asfalto", "abriu uma cratera na rua", "a calçada está toda quebrada",
        "o asfalto afundou", "a rua está cheia de buracos", "o meio fio está destruído",
        "o pavimento cedeu depois da obra", "a rua precisa de recapeamento", "o calçamento está solto",
        "os paralelepípedos estão soltos", "tem um desnível grande na calçada",
        "a rua de terra está intransitável, cheia de valeta", "o tapa buraco que fizeram já abriu de novo",
        "a calçada afundou e formou um degrau", "o asfalto está esfarelando e cheio de remendo",
        "tem um buraco que estoura pneu de carro",
    ],
    "residuos": [
        "tem lixo acumulado", "jogaram entulho no terreno baldio", "o caminhão da coleta não passou",
        "o mato está alto e tomando a calçada", "estão fazendo descarte irregular de lixo",
        "a lixeira da praça está transbordando", "deixaram sofá e móveis velhos na calçada",
        "a rua está muito suja, sem varrição", "a caçamba de entulho está abandonada",
        "o terreno precisa de capina, está cheio de mato", "a coleta de lixo está atrasada há dias",
        "tem sacos de lixo rasgados espalhados", "viraram a esquina em ponto de descarte de entulho",
        "a coleta seletiva não está passando", "tem resto de poda e galhos cortados amontoados no lixo",
        "o gari não varre a rua faz tempo",
    ],
    "agua": [
        "tem um vazamento de água na rua", "o esgoto está correndo a céu aberto", "o bueiro está entupido",
        "a boca de lobo está sem tampa", "a rua alaga toda vez que chove", "estamos sem água desde ontem",
        "o cano estourou e está jorrando água", "a água da torneira está saindo suja",
        "o esgoto está transbordando e voltando pelo ralo", "o bueiro está aberto",
        "a enchente invadiu as casas", "falta de água no bairro inteiro", "a galeria de água da chuva entupiu",
        "tem um vazamento na calçada desperdiçando água", "o córrego transbordou", "o esgoto está com cheiro forte e vazando",
    ],
    "arvores": [
        "tem uma árvore com risco de cair", "um galho grande está pendurado", "a árvore precisa de poda",
        "a raiz da árvore está levantando o chão", "caiu uma árvore", "o tronco da árvore está podre e oco",
        "os galhos estão encostando nos fios", "a praça está abandonada, com o jardim morrendo",
        "a árvore está com cupim e inclinada", "preciso de autorização para poda de árvore",
        "os galhos estão batendo no telhado", "a árvore está seca e morta", "o gramado do parque não é cortado",
        "as plantas do canteiro foram arrancadas", "uma árvore tombou com o vento", "a copa da árvore está cobrindo tudo",
    ],
    "transito": [
        "o semáforo está apagado", "o sinal está quebrado no cruzamento", "a faixa de pedestre está apagada",
        "falta sinalização na rua", "a placa de pare caiu", "precisa de uma lombada, os carros passam correndo",
        "o semáforo está piscando amarelo", "a pintura da sinalização sumiu do asfalto",
        "o quebra molas não tem pintura nem placa", "o cruzamento é perigoso e não tem sinal",
        "a placa de trânsito está pichada e ilegível", "o tempo do farol para pedestre é curto demais",
        "os carros estacionam em local proibido e travam o trânsito", "o semáforo de pedestre não funciona",
        "falta placa com o nome da rua e de mão única", "tiraram a placa de velocidade máxima",
    ],
    "transporte": [
        "o ônibus está sempre atrasado", "o ponto de ônibus não tem cobertura", "o motorista não parou no ponto",
        "o ônibus vem lotado todo dia", "a linha de ônibus foi cortada", "o terminal está sujo e sem banco",
        "o trem está demorando muito na estação", "o ônibus passa direto e não para",
        "tiraram horários da linha", "o motorista dirige de forma perigosa", "o bilhete não foi recarregado",
        "o ônibus quebrou e não mandaram outro", "a tarifa foi cobrada duas vezes",
        "o ponto de ônibus está sem placa das linhas", "espero mais de uma hora pelo ônibus",
        "o cobrador foi grosseiro com os passageiros",
    ],
    "saude": [
        "tem foco de dengue", "tem água parada com larva de mosquito", "apareceram ratos",
        "encontrei escorpião", "tem um animal morto na rua", "a casa abandonada virou criadouro de mosquito",
        "está cheio de barata saindo do terreno", "tem muito pombo fazendo sujeira",
        "o quintal do vizinho tem pneu com água parada", "apareceu caramujo africano",
        "tem cachorro morto apodrecendo", "tem infestação de ratos", "achei carrapato no parquinho",
        "a piscina da casa vazia está verde, cheia de mosquito", "tem morcego dentro do telhado",
        "pedimos dedetização contra o mosquito da dengue",
    ],
    "acessibilidade": [
        "a calçada não tem rampa para cadeirante", "falta guia rebaixada", "não tem piso tátil",
        "o elevador para cadeira de rodas está quebrado", "tem um degrau que impede cadeira de rodas",
        "a rampa de acesso é íngreme demais", "falta acessibilidade no prédio público",
        "pessoa com deficiência visual não consegue andar ali", "a vaga de deficiente está sempre ocupada",
        "o piso tátil está quebrado e leva para um poste", "não tem rampa na travessia",
        "o corrimão da rampa foi arrancado", "o banheiro adaptado está trancado",
        "cadeirante precisa andar na rua porque a calçada não tem acesso",
        "o semáforo não tem sinal sonoro para cego", "não há intérprete nem atendimento acessível",
    ],
    "barulho": [
        "tem som alto até de madrugada", "o bar faz barulho a noite toda", "música alta todo fim de semana",
        "tem baile com paredão de som", "a obra faz ruído fora do horário", "festa com barulho até amanhecer",
        "carro com som alto parado na rua", "a igreja usa caixa de som muito alta",
        "o vizinho faz barulho e não deixa ninguém dormir", "a oficina faz ruído o dia inteiro",
        "tem gritaria e música na praça de madrugada", "motos fazendo barulho com escapamento aberto",
        "o comércio coloca caixa de som na calçada", "perturbação do sossego toda noite",
        "soltam rojão e fogos de madrugada", "o gerador do prédio faz um barulho insuportável",
    ],
    "outros": [
        "preciso de ajuda com um problema", "quero falar com alguém da prefeitura", "ninguém resolve nada",
        "tenho uma dúvida sobre um documento", "quero saber sobre o IPTU", "como faço para tirar segunda via do carnê",
        "gostaria de uma informação", "quero fazer uma sugestão para a cidade", "preciso de uma certidão",
        "não sei onde reclamar", "quero saber o horário de atendimento", "meu vizinho construiu um muro no meu terreno",
        "quero matricular meu filho na creche", "preciso agendar uma consulta", "o problema continua igual",
        "quero elogiar o atendimento que recebi", "como consigo alvará para o meu comércio",
        "tem um cachorro abandonado e quero adotar", "quero saber de concurso público", "está tudo errado aqui",
    ],
}


def montar(aleatorio: random.Random, problema: str) -> str:
    partes = [aleatorio.choice(ABERTURAS), problema, aleatorio.choice(LOCAIS)]
    texto = " ".join(p for p in partes if p).strip()
    texto = texto[0].upper() + texto[1:]
    if not texto.endswith((".", "?", "!")):
        texto += "."
    complemento = aleatorio.choice(COMPLEMENTOS)
    if aleatorio.random() < 0.15:  # parte dos cidadãos escreve tudo em minúsculas e sem acento
        import unicodedata
        texto = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                        if unicodedata.category(c) != "Mn")
    return f"{texto} {complemento}".strip()


def gerar_treino() -> pd.DataFrame:
    aleatorio = random.Random(SEMENTE)
    linhas = []
    for categoria, problemas in PROBLEMAS.items():
        vistos: set[str] = set()
        while len(vistos) < POR_CATEGORIA:
            problema = problemas[len(vistos) % len(problemas)]
            vistos.add(montar(aleatorio, problema))
        linhas += [{"relato": texto, "categoria": categoria} for texto in sorted(vistos)]
    return pd.DataFrame(linhas)


def gerar_planilha_balcao(caminho: Path) -> None:
    pd.DataFrame([
        ["12/11/2026", "Vila Nova", "em frente ao nº 210",
         "Senhora idosa veio avisar que o esgoto está voltando pelo ralo da cozinha faz três dias."],
        ["12/11/2026", "Centro", "praça da matriz",
         "Morador reclama do bar da praça com música alta até as 4 da manhã toda sexta."],
        ["12/11/2026", "Jardim das Flores", "", "A rampa da calçada da UBS quebrou e o cadeirante não consegue subir."],
        ["13/11/2026", "Parque Industrial", "rua do campo", "Ônibus da linha 12 não passa no horário, hoje esperei 50 minutos."],
        ["13/11/2026", "Vila Nova", "", "Árvore enorme com galho rachado em cima do parquinho, risco de cair nas crianças."],
        ["13/11/2026", "Centro", "", "Quero saber se a prefeitura empresta cadeiras para festa da comunidade."],
    ], columns=["Data de abertura", "Bairro", "Ponto de referência", "Descrição"]).to_excel(caminho, index=False)


if __name__ == "__main__":
    treino = gerar_treino()
    treino.to_csv(RAIZ / "dados" / "treino.csv", index=False)
    print(f"dados/treino.csv: {len(treino)} relatos, {treino['categoria'].nunique()} categorias")
    gerar_planilha_balcao(RAIZ / "dados" / "exemplos" / "balcao_atendimento.xlsx")
    print("dados/exemplos/balcao_atendimento.xlsx gerada")
