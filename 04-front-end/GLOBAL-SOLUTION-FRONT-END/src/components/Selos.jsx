import { PRIORIDADES } from '../data/categorias.js';
import { rotuloEtapa } from '../services/solicitacoes.js';

// Cada prioridade tem cor, texto E forma própria: quem não distingue cores
// ainda consegue diferenciar pelo desenho e pela palavra.
const FORMAS = {
  urgente: <path d="M8 1 15 14H1z" />,
  alta: <path d="M8 1l7 7-7 7-7-7z" />,
  media: <circle cx="8" cy="8" r="6.5" />,
  baixa: <rect x="2" y="2" width="12" height="12" rx="1.5" />,
};

export function SeloPrioridade({ nivel }) {
  return (
    <span className={`selo selo--${nivel}`}>
      <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true" focusable="false">
        {FORMAS[nivel]}
      </svg>
      <span className="so-leitor">Prioridade </span>
      {PRIORIDADES[nivel].rotulo}
    </span>
  );
}

export function SeloEtapa({ status }) {
  return (
    <span className={`selo selo--etapa${status === 'concluida' ? ' selo--concluida' : ''}`}>
      {rotuloEtapa(status)}
    </span>
  );
}
