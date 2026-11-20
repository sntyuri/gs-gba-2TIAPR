// Cadastro e consulta de solicitações, persistidas no localStorage.

import { ler, gravar, gerarId } from './storage.js';
import { triar } from './ia.js';

const CHAVE = 'solicitacoes';
const CHAVE_CONTADOR = 'contador-protocolo';

// As etapas formam uma sequência: cada pedido avança da primeira para a última.
export const ETAPAS = [
  { id: 'recebida', rotulo: 'Recebida' },
  { id: 'triagem', rotulo: 'Em triagem' },
  { id: 'encaminhada', rotulo: 'Encaminhada ao órgão' },
  { id: 'concluida', rotulo: 'Concluída' },
];

export const rotuloEtapa = (id) => ETAPAS.find((etapa) => etapa.id === id)?.rotulo ?? id;

const listarTodas = () => ler(CHAVE, []);
const evento = (texto) => ({ data: new Date().toISOString(), texto });

function proximoProtocolo() {
  const numero = ler(CHAVE_CONTADOR, 0) + 1;
  gravar(CHAVE_CONTADOR, numero);
  return `ZL-${new Date().getFullYear()}-${String(numero).padStart(5, '0')}`;
}

export function listarSolicitacoes(usuarioId) {
  return listarTodas()
    .filter((item) => item.usuarioId === usuarioId)
    .sort((a, b) => b.criadoEm.localeCompare(a.criadoEm));
}

export function obterSolicitacao(id, usuarioId) {
  // Só devolve o pedido se ele pertencer a quem está logado.
  return listarTodas().find((item) => item.id === id && item.usuarioId === usuarioId) ?? null;
}

export function criarSolicitacao({ usuarioId, descricao, bairro, referencia, analise }) {
  const nova = {
    id: gerarId(),
    protocolo: proximoProtocolo(),
    usuarioId,
    descricao,
    bairro: bairro.trim(),
    referencia: referencia.trim(),
    analise,
    status: analise.revisaoHumana ? 'triagem' : 'encaminhada',
    criadoEm: new Date().toISOString(),
    historico: [
      evento('Solicitação recebida.'),
      evento(
        `Triagem por IA: ${analise.categoriaNome}, prioridade ${analise.prioridade}.` +
          (analise.revisaoHumana
            ? ' Classificação com baixa confiança: enviada para conferência humana.'
            : ` Encaminhada para ${analise.orgao}.`),
      ),
    ],
  };
  if (!gravar(CHAVE, [...listarTodas(), nova])) {
    throw new Error('Não foi possível salvar a solicitação neste navegador.');
  }
  return nova;
}

function atualizar(id, usuarioId, transformar) {
  let atualizada = null;
  const todas = listarTodas().map((item) => {
    if (item.id !== id || item.usuarioId !== usuarioId) return item;
    atualizada = transformar(item);
    return atualizada;
  });
  if (atualizada) gravar(CHAVE, todas);
  return atualizada;
}

// Demonstração: simula o andamento que, em produção, viria da prefeitura.
export function avancarEtapa(id, usuarioId) {
  return atualizar(id, usuarioId, (item) => {
    const indice = ETAPAS.findIndex((etapa) => etapa.id === item.status);
    const proxima = ETAPAS[indice + 1];
    if (!proxima) return item;
    const texto =
      proxima.id === 'concluida'
        ? `${item.analise.orgao} informou que o serviço foi concluído.`
        : `Classificação conferida. Encaminhada para ${item.analise.orgao}.`;
    return { ...item, status: proxima.id, historico: [...item.historico, evento(texto)] };
  });
}

// Supervisão humana: o cidadão pode corrigir a categoria escolhida pela IA.
export function corrigirCategoria(id, usuarioId, categoriaId) {
  return atualizar(id, usuarioId, (item) => {
    const analise = triar(item.descricao, { bairro: item.bairro, categoriaForcada: categoriaId });
    return {
      ...item,
      analise,
      historico: [
        ...item.historico,
        evento(`Categoria corrigida pelo cidadão para ${analise.categoriaNome}. Novo destino: ${analise.orgao}.`),
      ],
    };
  });
}

export function excluirSolicitacao(id, usuarioId) {
  gravar(
    CHAVE,
    listarTodas().filter((item) => !(item.id === id && item.usuarioId === usuarioId)),
  );
}

export function excluirSolicitacoesDoUsuario(usuarioId) {
  gravar(
    CHAVE,
    listarTodas().filter((item) => item.usuarioId !== usuarioId),
  );
}
