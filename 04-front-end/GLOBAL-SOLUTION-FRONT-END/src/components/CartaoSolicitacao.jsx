import { Link } from 'react-router-dom';
import Placa from './Placa.jsx';
import { SeloEtapa, SeloPrioridade } from './Selos.jsx';
import { formatarData } from '../services/formato.js';

// Recebe a solicitação por props e mostra o resumo na lista de consulta.
export default function CartaoSolicitacao({ solicitacao }) {
  const { id, protocolo, bairro, descricao, analise, status, criadoEm } = solicitacao;

  return (
    <li className="cartao-solicitacao">
      <Placa protocolo={protocolo} bairro={bairro} />
      <div className="cartao-solicitacao__corpo">
        <h3>
          <Link to={`/solicitacoes/${id}`}>{analise.categoriaNome}</Link>
        </h3>
        <p className="cartao-solicitacao__descricao">{descricao}</p>
        <p className="cartao-solicitacao__meta">
          <SeloPrioridade nivel={analise.prioridade} />
          <SeloEtapa status={status} />
          <span>Registrada em {formatarData(criadoEm)}</span>
        </p>
      </div>
    </li>
  );
}
