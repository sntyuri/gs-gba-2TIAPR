// Motor de triagem da Zela (IA SIMULADA).
//
// Recebe o relato em linguagem natural e devolve: categoria, prioridade,
// órgão responsável, prazo estimado, resposta em linguagem simples e a
// explicação de como chegou ao resultado.
//
// A "inteligência" aqui é um classificador por regras e pesos que roda no
// próprio navegador. Isso foi uma escolha de projeto:
//   - o relato do cidadão não sai do aparelho (proteção de dados);
//   - o resultado é explicável: mostramos os termos que pesaram na decisão;
//   - a demonstração funciona sem internet e sem chave de API.
//
// Para integrar um modelo real, basta trocar o corpo de `analisarSolicitacao`
// por uma chamada a um backend que devolva um objeto com o mesmo formato.
// (Nunca coloque chave de API no frontend: ela ficaria visível para qualquer um.)

import { CATEGORIAS, PRIORIDADES, buscarCategoria } from '../data/categorias.js';

export const MOTOR = 'zela-triagem-regras-v1';
const CONFIANCA_MINIMA = 55;
const PONTUACAO_MINIMA = 2;

// Sinais que aumentam a prioridade, independentemente da categoria.
const SINAIS = [
  {
    id: 'risco',
    rotulo: 'Risco imediato para as pessoas',
    motivo: 'há sinais de risco imediato para as pessoas',
    peso: 3,
    termos: [
      'fio solto', 'fio caido', 'fio exposto', 'choque', 'curto circuito', 'faisca*',
      'incendio', 'fogo', 'desab*', 'desliz*', 'explos*', 'gas', 'ferid*', 'machuc*',
      'acidente', 'afog*', 'risco de vida', 'risco de morte', 'bueiro aberto',
      'sem tampa', 'cratera', 'caiu', 'cair*', 'queda',
    ],
  },
  {
    id: 'vulneraveis',
    rotulo: 'Pessoas vulneráveis ou local sensível',
    motivo: 'afeta pessoas mais vulneráveis ou um local sensível, como escola ou unidade de saúde',
    peso: 2,
    termos: [
      'crianca', 'idos*', 'escola', 'creche', 'hospital', 'ubs', 'posto de saude',
      'cadeirante', 'deficien*', 'gestante', 'gravida', 'bebe',
    ],
  },
  {
    id: 'perigo',
    rotulo: 'Relato de perigo',
    motivo: 'o relato menciona perigo',
    peso: 2,
    termos: ['perig*', 'risco', 'assalt*', 'inseguranca', 'urgente', 'urgencia', 'emergencia'],
  },
  {
    id: 'alcance',
    rotulo: 'Afeta muita gente',
    motivo: 'afeta muita gente ou a circulação',
    peso: 1,
    termos: [
      'rua inteira', 'rua toda', 'bairro inteiro', 'bairro todo', 'todo mundo',
      'varios moradores', 'muitos moradores', 'interdit*', 'bloque*', 'transito parado',
      'enorme', 'gigante', 'alag*', 'enchente',
    ],
  },
  {
    id: 'duracao',
    rotulo: 'Problema antigo ou repetido',
    motivo: 'o problema já dura bastante tempo ou se repete',
    peso: 1,
    termos: [
      /\bha (?:mais de )?(?:\w+ )?(?:dias|semanas?|mes|meses|anos?)\b/,
      /\bfaz (?:\w+ )?(?:tempo|dias|semanas|meses|anos)\b/,
      'toda noite', 'todo dia', 'todos os dias', 'toda vez', 'de novo', 'novamente',
      'outra vez', 'ja reclamei', 'ja abri',
    ],
  },
];

// Minúsculas e sem acento, mantendo o mesmo tamanho do texto original
// (assim conseguimos mostrar ao cidadão o trecho exatamente como ele escreveu).
export function normalizar(texto) {
  return String(texto ?? '')
    .normalize('NFC')
    .replace(/[À-ſ]/g, (letra) => letra.normalize('NFD')[0])
    .toLowerCase();
}

const escapar = (trecho) => trecho.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function criarPadrao(termo) {
  if (termo instanceof RegExp) return termo;
  const aceitaTerminacao = termo.endsWith('*');
  const palavras = (aceitaTerminacao ? termo.slice(0, -1) : termo).split(' ');
  const partes = palavras.map((palavra, indice) => {
    const ultima = indice === palavras.length - 1;
    return escapar(palavra) + (ultima && aceitaTerminacao ? '\\w*' : '(?:s|es)?');
  });
  return new RegExp(`\\b${partes.join('[\\s-]+')}\\b`);
}

// Devolve o trecho original que casou com o termo, ou null.
function encontrar(termo, textoNormalizado, textoOriginal) {
  const achado = criarPadrao(termo).exec(textoNormalizado);
  if (!achado) return null;
  return textoOriginal.slice(achado.index, achado.index + achado[0].length).trim();
}

function pontuarCategorias(textoNormalizado, textoOriginal) {
  return CATEGORIAS.filter((categoria) => categoria.termos.length > 0)
    .map((categoria) => {
      const trechos = [];
      let pontos = 0;
      categoria.termos.forEach(([termo, peso]) => {
        const trecho = encontrar(termo, textoNormalizado, textoOriginal);
        if (trecho) {
          pontos += peso;
          trechos.push(trecho);
        }
      });
      return { categoria, pontos, trechos };
    })
    .sort((a, b) => b.pontos - a.pontos);
}

function detectarSinais(textoNormalizado, textoOriginal) {
  return SINAIS.map((sinal) => {
    const trechos = sinal.termos
      .map((termo) => encontrar(termo, textoNormalizado, textoOriginal))
      .filter(Boolean);
    return { ...sinal, trechos: [...new Set(trechos)] };
  }).filter((sinal) => sinal.trechos.length > 0);
}

function definirPrioridade(categoria, sinais) {
  const pontos = categoria.prioridadeBase + sinais.reduce((soma, sinal) => soma + sinal.peso, 0);
  const haRisco = sinais.some((sinal) => sinal.id === 'risco');
  let nivel = 'baixa';
  if ((haRisco && pontos >= 5) || pontos >= 8) nivel = 'urgente';
  else if (haRisco || pontos >= 4) nivel = 'alta';
  else if (pontos >= 2) nivel = 'media';
  return { nivel, pontos, haRisco };
}

function calcularPrazo(categoria, nivel) {
  const dias = {
    urgente: 1,
    alta: Math.max(1, Math.ceil(categoria.prazoBase * 0.4)),
    media: categoria.prazoBase,
    baixa: Math.ceil(categoria.prazoBase * 1.5),
  }[nivel];
  return { dias, texto: dias === 1 ? 'até 1 dia útil' : `até ${dias} dias úteis` };
}

function juntar(lista) {
  if (lista.length <= 1) return lista.join('');
  return `${lista.slice(0, -1).join(', ')} e ${lista.at(-1)}`;
}

// Triagem síncrona e pura: fácil de testar (veja tests/ia.test.js).
export function triar(descricao, { bairro = '', categoriaForcada = null } = {}) {
  const original = String(descricao ?? '').normalize('NFC');
  const texto = normalizar(original);

  const ranking = pontuarCategorias(texto, original);
  const [primeira, segunda] = ranking;

  let escolhida = primeira;
  let confianca = Math.min(
    97,
    Math.max(30, 40 + 10 * (primeira.pontos - segunda.pontos) + 5 * Math.min(primeira.pontos, 6)),
  );
  let revisaoHumana = confianca < CONFIANCA_MINIMA;

  if (primeira.pontos < PONTUACAO_MINIMA) {
    escolhida = { categoria: buscarCategoria('outros'), pontos: 0, trechos: [] };
    confianca = 20;
    revisaoHumana = true;
  }

  const corrigidaPeloCidadao = Boolean(categoriaForcada);
  if (corrigidaPeloCidadao) {
    const categoria = buscarCategoria(categoriaForcada);
    const noRanking = ranking.find((item) => item.categoria.id === categoria.id);
    escolhida = noRanking ?? { categoria, pontos: 0, trechos: [] };
    confianca = null;
    revisaoHumana = false;
  }

  const { categoria } = escolhida;
  const sinais = detectarSinais(texto, original);
  const prioridade = definirPrioridade(categoria, sinais);
  const prazo = calcularPrazo(categoria, prioridade.nivel);
  const rotuloPrioridade = PRIORIDADES[prioridade.nivel].rotulo.toLowerCase();

  const motivos = sinais.length
    ? juntar(sinais.map((sinal) => sinal.motivo))
    : 'não identifiquei sinais de risco imediato no relato';

  let abertura = `Entendi que o seu pedido é sobre ${categoria.nome.toLowerCase()}.`;
  if (corrigidaPeloCidadao) {
    abertura = `Você indicou que o pedido é sobre ${categoria.nome.toLowerCase()}, e a classificação foi atualizada.`;
  } else if (categoria.id === 'outros') {
    abertura =
      'Não consegui identificar com segurança o tipo de problema. Para ajudar, descreva o que está acontecendo, onde e desde quando.';
  } else if (revisaoHumana) {
    abertura = `Parece que o seu pedido é sobre ${categoria.nome.toLowerCase()}, mas não tenho certeza.`;
  }

  let encaminhamento = `O pedido segue para o órgão responsável (${categoria.orgao}), com previsão de resposta em ${prazo.texto}.`;
  if (categoria.id === 'outros') {
    encaminhamento = `Uma pessoa da ${categoria.orgao} vai ler o relato e direcionar para a área certa. A previsão de resposta é de ${prazo.texto}.`;
  } else if (revisaoHumana) {
    encaminhamento = `Por isso, uma pessoa da Central de Atendimento vai conferir a classificação antes de encaminhar ao órgão responsável (${categoria.orgao}). A previsão de resposta é de ${prazo.texto}.`;
  }

  const resposta = `${abertura} Classifiquei a prioridade como ${rotuloPrioridade} porque ${motivos}. ${encaminhamento}`;

  const proximosPassos = [
    'Guarde o número do protocolo para acompanhar o pedido.',
    revisaoHumana
      ? 'Uma pessoa da Central de Atendimento confere a classificação feita pela IA.'
      : `${categoria.orgao} recebe o pedido e programa a vistoria.`,
    'Você acompanha cada etapa em "Minhas solicitações".',
  ];

  return {
    motor: MOTOR,
    categoriaId: categoria.id,
    categoriaNome: categoria.nome,
    orgao: categoria.orgao,
    confianca,
    revisaoHumana,
    corrigidaPeloCidadao,
    prioridade: prioridade.nivel,
    pontosPrioridade: prioridade.pontos,
    emergencia: prioridade.haRisco,
    prazoDias: prazo.dias,
    prazoTexto: prazo.texto,
    titulo: bairro.trim() ? `${categoria.nome} em ${bairro.trim()}` : categoria.nome,
    resposta,
    proximosPassos,
    orientacoes: categoria.orientacoes,
    termos: [...new Set(escolhida.trechos)],
    sinais: sinais.map(({ id, rotulo, peso, trechos }) => ({ id, rotulo, peso, trechos })),
    alternativas: ranking
      .filter((item) => item.pontos > 0 && item.categoria.id !== categoria.id)
      .slice(0, 2)
      .map((item) => ({ categoriaId: item.categoria.id, nome: item.categoria.nome })),
  };
}

// Versão assíncrona usada pelas telas. O atraso simula o tempo de resposta
// de um serviço de IA e é o ponto de troca para uma integração real.
export function analisarSolicitacao(descricao, opcoes = {}, atrasoMs = 900) {
  return new Promise((resolver) => {
    setTimeout(() => resolver(triar(descricao, opcoes)), atrasoMs);
  });
}
