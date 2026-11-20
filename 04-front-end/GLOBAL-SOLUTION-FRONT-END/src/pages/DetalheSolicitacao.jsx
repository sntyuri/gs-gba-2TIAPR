import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import Aviso from '../components/Aviso.jsx';
import EtapasStatus from '../components/EtapasStatus.jsx';
import Placa from '../components/Placa.jsx';
import RespostaIA from '../components/RespostaIA.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { CATEGORIAS } from '../data/categorias.js';
import { useTituloPagina } from '../hooks/useTituloPagina.js';
import { formatarDataHora } from '../services/formato.js';
import {
  avancarEtapa,
  corrigirCategoria,
  excluirSolicitacao,
  obterSolicitacao,
} from '../services/solicitacoes.js';

export default function DetalheSolicitacao() {
  const { id } = useParams();
  const { usuario } = useAuth();
  const local = useLocation();
  const navegar = useNavigate();

  const [solicitacao, setSolicitacao] = useState(() => obterSolicitacao(id, usuario.id));
  const [novaCategoria, setNovaCategoria] = useState(solicitacao?.analise.categoriaId ?? '');
  const [mensagem, setMensagem] = useState(local.state?.recemCriada ? 'criada' : '');
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);

  useTituloPagina(solicitacao ? `Solicitação ${solicitacao.protocolo}` : 'Solicitação não encontrada');

  if (!solicitacao) {
    return (
      <div className="conteiner secao">
        <h1>Solicitação não encontrada</h1>
        <p>Ela pode ter sido excluída ou pertencer a outra conta deste navegador.</p>
        <Link to="/solicitacoes" className="botao botao--secundario">
          Ver minhas solicitações
        </Link>
      </div>
    );
  }

  const { analise } = solicitacao;
  const concluida = solicitacao.status === 'concluida';

  function aoCorrigir(evento) {
    evento.preventDefault();
    if (novaCategoria === analise.categoriaId) return;
    setSolicitacao(corrigirCategoria(solicitacao.id, usuario.id, novaCategoria));
    setMensagem('corrigida');
  }

  function aoAvancar() {
    setSolicitacao(avancarEtapa(solicitacao.id, usuario.id));
    setMensagem('avancou');
  }

  function aoExcluir() {
    excluirSolicitacao(solicitacao.id, usuario.id);
    navegar('/solicitacoes', { replace: true });
  }

  return (
    <div className="conteiner conteiner--medio secao">
      <p>
        <Link to="/solicitacoes">Voltar para minhas solicitações</Link>
      </p>

      <div className="detalhe__topo">
        <Placa protocolo={solicitacao.protocolo} bairro={solicitacao.bairro} grande />
        <div>
          <h1>{analise.categoriaNome}</h1>
          <p className="texto-suave">Registrada em {formatarDataHora(solicitacao.criadoEm)}</p>
        </div>
      </div>

      {/* Uma única região viva anuncia o resultado de cada ação. */}
      <div role="status">
        {mensagem === 'criada' && (
          <Aviso tipo="sucesso" titulo="Solicitação registrada">
            <p>Guarde o protocolo {solicitacao.protocolo} para acompanhar.</p>
          </Aviso>
        )}
        {mensagem === 'corrigida' && (
          <Aviso tipo="sucesso" titulo="Categoria corrigida">
            <p>A prioridade, o órgão responsável e o prazo foram recalculados.</p>
          </Aviso>
        )}
        {mensagem === 'avancou' && (
          <Aviso tipo="info" titulo="Andamento atualizado">
            <p>Etapa simulada para a demonstração.</p>
          </Aviso>
        )}
      </div>

      <EtapasStatus status={solicitacao.status} />

      <section className="relato">
        <h2>Seu relato</h2>
        <blockquote>{solicitacao.descricao}</blockquote>
        {solicitacao.referencia && (
          <p className="texto-suave">Ponto de referência: {solicitacao.referencia}</p>
        )}
      </section>

      <RespostaIA analise={analise} nivelTitulo={2} />

      {!concluida && (
        <section className="bloco">
          <h2>A IA errou o tipo de problema?</h2>
          <p>Você conhece a situação melhor do que a IA. Corrija e o pedido é redirecionado.</p>
          <form onSubmit={aoCorrigir} className="linha-formulario">
            <div className="campo">
              <label htmlFor="nova-categoria">Tipo de problema correto</label>
              <select
                id="nova-categoria"
                value={novaCategoria}
                onChange={(evento) => setNovaCategoria(evento.target.value)}
              >
                {CATEGORIAS.map((categoria) => (
                  <option key={categoria.id} value={categoria.id}>
                    {categoria.nome}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="botao botao--secundario"
              disabled={novaCategoria === analise.categoriaId}
            >
              Corrigir categoria
            </button>
          </form>
        </section>
      )}

      <section className="bloco">
        <h2>Histórico</h2>
        <ol className="historico">
          {solicitacao.historico.map((evento, indice) => (
            <li key={`${evento.data}-${indice}`}>
              <time dateTime={evento.data}>{formatarDataHora(evento.data)}</time>
              <span>{evento.texto}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="bloco bloco--demonstracao">
        <h2>Área de demonstração</h2>
        <p>
          Em um sistema real, o andamento viria da prefeitura. Aqui, o botão simula a próxima etapa
          para mostrar o acompanhamento.
        </p>
        <div className="acoes">
          <button type="button" className="botao botao--secundario" onClick={aoAvancar} disabled={concluida}>
            {concluida ? 'Pedido concluído' : 'Simular próxima etapa'}
          </button>

          {confirmandoExclusao ? (
            <span className="confirmacao" role="group" aria-label="Confirmar exclusão">
              <span>Excluir este pedido de vez?</span>
              <button type="button" className="botao botao--perigo" onClick={aoExcluir}>
                Excluir solicitação
              </button>
              <button
                type="button"
                className="botao botao--secundario"
                onClick={() => setConfirmandoExclusao(false)}
              >
                Manter
              </button>
            </span>
          ) : (
            <button type="button" className="botao botao--secundario" onClick={() => setConfirmandoExclusao(true)}>
              Excluir solicitação
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
