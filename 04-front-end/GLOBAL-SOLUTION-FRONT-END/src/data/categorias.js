// Base de conhecimento do motor de triagem.
//
// Cada categoria tem termos com peso (1 = indício fraco, 3 = indício forte).
// Os termos ficam sem acento e em minúsculas, porque o texto do cidadão é
// normalizado antes da comparação. Um "*" no fim aceita qualquer terminação
// (ex.: "alag*" encontra alagou, alagada, alagamento).
//
// Órgãos e prazos são ILUSTRATIVOS: representam uma prefeitura fictícia.

export const CATEGORIAS = [
  {
    id: 'iluminacao',
    nome: 'Iluminação e rede elétrica',
    orgao: 'Departamento de Iluminação Pública',
    prazoBase: 5,
    prioridadeBase: 1,
    termos: [
      ['iluminacao', 3], ['luz apagada', 3], ['luz queimada', 3], ['poste', 2],
      ['lampada', 2], ['luminaria', 2], ['sem luz', 2], ['fio', 2], ['fiacao', 2],
      ['faisca*', 2], ['apagad*', 1], ['escur*', 1],
    ],
    orientacoes: [
      'Não toque em fios soltos ou caídos, mesmo que pareçam desligados.',
      'Se puder, anote o número da plaqueta do poste: isso agiliza o reparo.',
    ],
  },
  {
    id: 'vias',
    nome: 'Ruas e calçadas',
    orgao: 'Secretaria de Obras e Vias Públicas',
    prazoBase: 10,
    prioridadeBase: 1,
    termos: [
      ['buraco', 3], ['cratera', 3], ['asfalto', 2], ['paviment*', 2], ['calcada', 2],
      ['meio fio', 3], ['afund*', 2], ['recape*', 2], ['paralelepipedo', 2], ['tampa solta', 2],
      ['desnivel', 1],
    ],
    orientacoes: [
      'Evite passar a pé ou de moto perto do buraco, principalmente à noite e com chuva.',
      'Não tente tapar o buraco por conta própria com entulho ou madeira.',
    ],
  },
  {
    id: 'residuos',
    nome: 'Lixo e limpeza urbana',
    orgao: 'Serviço de Limpeza Urbana',
    prazoBase: 4,
    prioridadeBase: 1,
    termos: [
      ['lixo', 3], ['entulho', 3], ['mato alto', 3], ['coleta', 2], ['descarte', 2],
      ['sujeira', 2], ['terreno baldio', 2], ['lixeira', 2], ['cacamba', 2],
      ['varricao', 2], ['capina', 2], ['moveis velhos', 2], ['sofa', 1],
    ],
    orientacoes: [
      'Coloque o lixo na calçada apenas no dia e horário da coleta.',
      'Móveis e entulho não vão no lixo comum: aguarde a retirada ou use um ecoponto.',
    ],
  },
  {
    id: 'agua',
    nome: 'Água, esgoto e drenagem',
    orgao: 'Companhia de Saneamento e Drenagem',
    prazoBase: 3,
    prioridadeBase: 2,
    termos: [
      ['vazamento', 3], ['esgoto', 3], ['bueiro', 3], ['boca de lobo', 3], ['alag*', 3],
      ['enchente', 3], ['falta de agua', 3], ['sem agua', 3], ['cano', 2],
      ['agua suja', 2], ['entupid*', 2], ['transbord*', 2],
    ],
    orientacoes: [
      'Não atravesse ruas alagadas, a pé ou de carro: pode haver bueiros abertos.',
      'Evite contato com água de esgoto ou de enchente.',
    ],
  },
  {
    id: 'arvores',
    nome: 'Árvores e áreas verdes',
    orgao: 'Secretaria do Verde e Meio Ambiente',
    prazoBase: 12,
    prioridadeBase: 1,
    termos: [
      ['arvore', 3], ['galho', 3], ['poda', 3], ['raiz', 2], ['tronco', 2],
      ['praca', 2], ['parque', 1], ['jardim', 1],
    ],
    orientacoes: [
      'Não faça a poda por conta própria: árvores em área pública precisam de equipe autorizada.',
      'Mantenha distância de galhos encostados na rede elétrica.',
    ],
  },
  {
    id: 'transito',
    nome: 'Trânsito e sinalização',
    orgao: 'Departamento de Trânsito e Sinalização',
    prazoBase: 5,
    prioridadeBase: 2,
    termos: [
      ['semaforo', 3], ['sinal quebrado', 3], ['sinal apagado', 3], ['sinalizacao', 3],
      ['faixa de pedestre', 3], ['placa', 2], ['lombada', 2], ['quebra molas', 2],
      ['cruzamento', 2], ['transito', 1], ['farol', 1],
    ],
    orientacoes: [
      'Com o semáforo apagado, trate o cruzamento como parada obrigatória.',
      'Redobre a atenção ao atravessar: motoristas podem não respeitar a preferência.',
    ],
  },
  {
    id: 'transporte',
    nome: 'Transporte público',
    orgao: 'Secretaria de Mobilidade e Transportes',
    prazoBase: 7,
    prioridadeBase: 1,
    termos: [
      ['onibus', 3], ['ponto de onibus', 2], ['motorista', 2], ['atras*', 2],
      ['terminal', 2], ['estacao', 2], ['trem', 2], ['linha', 1], ['lotad*', 1],
      ['tarifa', 1], ['bilhete', 1],
    ],
    orientacoes: [
      'Anote a linha, o horário e, se possível, o número do veículo.',
    ],
  },
  {
    id: 'saude',
    nome: 'Saúde ambiental e zoonoses',
    orgao: 'Vigilância em Saúde Ambiental',
    prazoBase: 3,
    prioridadeBase: 2,
    termos: [
      ['dengue', 3], ['agua parada', 3], ['mosquito', 3], ['rato', 3], ['escorpi*', 3],
      ['animal morto', 3], ['barata', 2], ['caramujo', 2], ['carrapato', 2],
      ['foco', 1], ['pombo', 1],
    ],
    orientacoes: [
      'Elimine água parada em vasos, pneus e calhas dentro do seu terreno.',
      'Não tente capturar escorpiões ou ratos com as mãos.',
    ],
  },
  {
    id: 'acessibilidade',
    nome: 'Acessibilidade',
    orgao: 'Secretaria da Pessoa com Deficiência e Acessibilidade',
    prazoBase: 10,
    prioridadeBase: 2,
    termos: [
      ['acessibilidade', 3], ['rampa', 3], ['cadeira de rodas', 3], ['piso tatil', 3],
      ['guia rebaixada', 3], ['cadeirante', 2], ['degrau', 2], ['elevador', 2],
      ['deficien*', 1],
    ],
    orientacoes: [
      'Descreva o trajeto bloqueado: isso ajuda a equipe a planejar a adequação completa.',
    ],
  },
  {
    id: 'barulho',
    nome: 'Barulho e perturbação do sossego',
    orgao: 'Fiscalização de Posturas Municipais',
    prazoBase: 7,
    prioridadeBase: 0,
    termos: [
      ['barulho', 3], ['som alto', 3], ['musica alta', 3], ['ruido', 2], ['baile', 2],
      ['paredao', 2], ['festa', 1],
    ],
    orientacoes: [
      'Anote os dias e horários em que o barulho acontece.',
      'Evite confronto direto: a fiscalização faz a abordagem.',
    ],
  },
  {
    id: 'outros',
    nome: 'Outros assuntos',
    orgao: 'Central de Atendimento ao Cidadão',
    prazoBase: 7,
    prioridadeBase: 1,
    termos: [],
    orientacoes: [
      'Uma pessoa da central vai ler o seu relato e direcionar para a área certa.',
    ],
  },
];

export function buscarCategoria(id) {
  return CATEGORIAS.find((categoria) => categoria.id === id) ?? CATEGORIAS.at(-1);
}

export const PRIORIDADES = {
  urgente: { rotulo: 'Urgente', ordem: 0 },
  alta: { rotulo: 'Alta', ordem: 1 },
  media: { rotulo: 'Média', ordem: 2 },
  baixa: { rotulo: 'Baixa', ordem: 3 },
};
