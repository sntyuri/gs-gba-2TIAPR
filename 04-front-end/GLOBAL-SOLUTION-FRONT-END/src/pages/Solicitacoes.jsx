import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import CartaoSolicitacao from '../components/CartaoSolicitacao.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { CATEGORIAS, PRIORIDADES } from '../data/categorias.js';
import { useTituloPagina } from '../hooks/useTituloPagina.js';
import { normalizar } from '../services/ia.js';
import { ETAPAS, listarSolicitacoes } from '../services/solicitacoes.js';

const FILTROS_INICIAIS = { busca: '', categoria: '', prioridade: '', status: '', ordem: 'recentes' };

export default function Solicitacoes() {
  useTituloPagina('Minhas solicitações');
  const { usuario } = useAuth();
  const [solicitacoes] = useState(() => listarSolicitacoes(usuario.id));
  const [filtros, setFiltros] = useState(FILTROS_INICIAIS);

  function aoMudar(evento) {
    const { name, value } = evento.target;
    setFiltros((atual) => ({ ...atual, [name]: value }));
  }

  const visiveis = useMemo(() => {
    const busca = normalizar(filtros.busca.trim());
    const filtradas = solicitacoes.filter((item) => {
      if (filtros.categoria && item.analise.categoriaId !== filtros.categoria) return false;
      if (filtros.prioridade && item.analise.prioridade !== filtros.prioridade) return false;
      if (filtros.status && item.status !== filtros.status) return false;
      if (!busca) return true;
      // A busca ignora acentos e maiúsculas e olha protocolo, bairro e relato.
      return normalizar(`${item.protocolo} ${item.bairro} ${item.descricao}`).includes(busca);
    });
    if (filtros.ordem === 'prioridade') {
      return [...filtradas].sort(
        (a, b) => PRIORIDADES[a.analise.prioridade].ordem - PRIORIDADES[b.analise.prioridade].ordem,
      );
    }
    return filtradas;
  }, [solicitacoes, filtros]);

  const temFiltro = filtros.busca || filtros.categoria || filtros.prioridade || filtros.status;

  if (solicitacoes.length === 0) {
    return (
      <div className="conteiner secao">
        <h1>Minhas solicitações</h1>
        <div className="vazio">
          <h2>Nenhum pedido registrado ainda</h2>
          <p>Quando você registrar um pedido, ele aparece aqui com o protocolo e o andamento.</p>
          <Link to="/solicitacoes/nova" className="botao botao--primario">
            Registrar uma solicitação
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="conteiner secao">
      <div className="titulo-com-acao">
        <h1>Minhas solicitações</h1>
        <Link to="/solicitacoes/nova" className="botao botao--primario">
          Registrar uma solicitação
        </Link>
      </div>

      <form className="filtros" role="search" aria-label="Filtrar solicitações" onSubmit={(e) => e.preventDefault()}>
        <div className="campo filtros__busca">
          <label htmlFor="busca">Buscar por protocolo, bairro ou palavra do relato</label>
          <input id="busca" name="busca" type="search" value={filtros.busca} onChange={aoMudar} />
        </div>
        <div className="campo">
          <label htmlFor="categoria">Tipo de problema</label>
          <select id="categoria" name="categoria" value={filtros.categoria} onChange={aoMudar}>
            <option value="">Todos</option>
            {CATEGORIAS.map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="prioridade">Prioridade</label>
          <select id="prioridade" name="prioridade" value={filtros.prioridade} onChange={aoMudar}>
            <option value="">Todas</option>
            {Object.entries(PRIORIDADES).map(([id, prioridade]) => (
              <option key={id} value={id}>
                {prioridade.rotulo}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="status">Andamento</label>
          <select id="status" name="status" value={filtros.status} onChange={aoMudar}>
            <option value="">Todos</option>
            {ETAPAS.slice(1).map((etapa) => (
              <option key={etapa.id} value={etapa.id}>
                {etapa.rotulo}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="ordem">Ordenar por</label>
          <select id="ordem" name="ordem" value={filtros.ordem} onChange={aoMudar}>
            <option value="recentes">Mais recentes</option>
            <option value="prioridade">Maior prioridade</option>
          </select>
        </div>
      </form>

      {/* role="status" faz o leitor de tela anunciar o total quando o filtro muda. */}
      <p role="status" className="contagem">
        {visiveis.length === 1
          ? '1 solicitação encontrada'
          : `${visiveis.length} solicitações encontradas`}
        {temFiltro && (
          <>
            {' '}
            <button type="button" className="link" onClick={() => setFiltros(FILTROS_INICIAIS)}>
              Limpar filtros
            </button>
          </>
        )}
      </p>

      {visiveis.length === 0 ? (
        <div className="vazio">
          <h2>Nenhum pedido combina com esses filtros</h2>
          <p>Tente outra palavra ou limpe os filtros para ver todos os pedidos.</p>
        </div>
      ) : (
        <ul className="lista-solicitacoes">
          {visiveis.map((solicitacao) => (
            <CartaoSolicitacao key={solicitacao.id} solicitacao={solicitacao} />
          ))}
        </ul>
      )}
    </div>
  );
}
