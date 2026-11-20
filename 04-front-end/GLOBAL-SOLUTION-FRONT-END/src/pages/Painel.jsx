import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Aviso from '../components/Aviso.jsx';
import CartaoSolicitacao from '../components/CartaoSolicitacao.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useTituloPagina } from '../hooks/useTituloPagina.js';
import { listarSolicitacoes } from '../services/solicitacoes.js';

export default function Painel() {
  useTituloPagina('Painel');
  const { usuario } = useAuth();
  const local = useLocation();
  const [solicitacoes] = useState(() => listarSolicitacoes(usuario.id));

  // Números derivados do estado: não precisam de um estado próprio.
  const emAndamento = solicitacoes.filter((item) => item.status !== 'concluida');
  const prioritarias = emAndamento.filter((item) =>
    ['urgente', 'alta'].includes(item.analise.prioridade),
  );
  const concluidas = solicitacoes.length - emAndamento.length;

  return (
    <div className="conteiner secao">
      <h1>Olá, {usuario.nome.split(' ')[0]}</h1>

      {local.state?.boasVindas && (
        <Aviso tipo="sucesso" anunciar>
          <p>Conta criada. Você já pode registrar o primeiro pedido.</p>
        </Aviso>
      )}

      {solicitacoes.length === 0 ? (
        <div className="vazio">
          <h2>Você ainda não registrou nenhum pedido</h2>
          <p>
            Descreva um problema do seu bairro e veja a triagem: tipo, prioridade, órgão responsável
            e prazo.
          </p>
          <Link to="/solicitacoes/nova" className="botao botao--primario">
            Registrar uma solicitação
          </Link>
        </div>
      ) : (
        <>
          <dl className="resumo">
            <div>
              <dt>Em andamento</dt>
              <dd>{emAndamento.length}</dd>
            </div>
            <div>
              <dt>Com prioridade alta ou urgente</dt>
              <dd>{prioritarias.length}</dd>
            </div>
            <div>
              <dt>Concluídas</dt>
              <dd>{concluidas}</dd>
            </div>
          </dl>

          <div className="titulo-com-acao">
            <h2>Pedidos mais recentes</h2>
            <Link to="/solicitacoes/nova" className="botao botao--primario">
              Registrar uma solicitação
            </Link>
          </div>
          <ul className="lista-solicitacoes">
            {solicitacoes.slice(0, 3).map((solicitacao) => (
              <CartaoSolicitacao key={solicitacao.id} solicitacao={solicitacao} />
            ))}
          </ul>
          {solicitacoes.length > 3 && (
            <p>
              <Link to="/solicitacoes">Ver todas as {solicitacoes.length} solicitações</Link>
            </p>
          )}
        </>
      )}
    </div>
  );
}
