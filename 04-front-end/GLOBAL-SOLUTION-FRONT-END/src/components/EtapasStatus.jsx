import { ETAPAS } from '../services/solicitacoes.js';

// Linha do tempo do pedido. É uma lista ordenada porque as etapas
// acontecem em sequência; a atual é marcada com aria-current.
export default function EtapasStatus({ status }) {
  // Com o pedido concluído, todas as etapas (inclusive a última) ficam marcadas como feitas.
  const concluido = status === 'concluida';
  const atual = concluido ? ETAPAS.length : ETAPAS.findIndex((etapa) => etapa.id === status);

  return (
    <ol className="etapas" aria-label="Andamento da solicitação">
      {ETAPAS.map((etapa, indice) => {
        const situacao = indice < atual ? 'feita' : indice === atual ? 'atual' : 'pendente';
        return (
          <li
            key={etapa.id}
            className={`etapas__item etapas__item--${situacao}`}
            aria-current={situacao === 'atual' ? 'step' : undefined}
          >
            <span className="etapas__marca" aria-hidden="true">
              {situacao === 'feita' ? '✓' : indice + 1}
            </span>
            <span>
              {etapa.rotulo}
              <span className="so-leitor">
                {situacao === 'feita' ? ' (concluída)' : situacao === 'atual' ? ' (etapa atual)' : ' (pendente)'}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
