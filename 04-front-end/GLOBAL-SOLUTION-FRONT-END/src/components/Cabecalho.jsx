import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { usePreferencias } from '../hooks/usePreferencias.js';

const LINKS_PUBLICOS = [
  { para: '/', rotulo: 'Início' },
  { para: '/sobre', rotulo: 'Sobre o projeto' },
  { para: '/privacidade', rotulo: 'Privacidade' },
];

const LINKS_LOGADO = [
  { para: '/painel', rotulo: 'Painel' },
  { para: '/solicitacoes/nova', rotulo: 'Nova solicitação' },
  { para: '/solicitacoes', rotulo: 'Minhas solicitações' },
  { para: '/sobre', rotulo: 'Sobre o projeto' },
  { para: '/privacidade', rotulo: 'Privacidade' },
];

export default function Cabecalho() {
  const { usuario } = useAuth();
  const { preferencias, alternar } = usePreferencias();
  const navegar = useNavigate();
  const links = usuario ? LINKS_LOGADO : LINKS_PUBLICOS;


  return (
    <header className="cabecalho">
      <div className="faixa-leitura">
        <div className="conteiner faixa-leitura__conteudo">
          <span id="rotulo-leitura">Ajustes de leitura</span>
          <div role="group" aria-labelledby="rotulo-leitura" className="faixa-leitura__botoes">
            <button
              type="button"
              className="alternador"
              aria-pressed={preferencias.letraMaior}
              onClick={() => alternar('letraMaior')}
            >
              Letra maior
            </button>
            <button
              type="button"
              className="alternador"
              aria-pressed={preferencias.altoContraste}
              onClick={() => alternar('altoContraste')}
            >
              Alto contraste
            </button>
          </div>
        </div>
      </div>

      <div className="conteiner cabecalho__barra">
        <Link to={usuario ? '/painel' : '/'} className="marca" aria-label="Zela, página inicial">
          <span className="marca__placa">Zela</span>
          <span className="marca__texto">Zeladoria urbana com IA</span>
        </Link>

        <nav aria-label="Principal" className="menu">
          <ul>
            {links.map((link) => (
              <li key={link.para}>
                {/* "end" evita que "Minhas solicitações" fique ativa em "Nova solicitação". */}
                <NavLink to={link.para} end>
                  {link.rotulo}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="cabecalho__conta">
          {usuario ? (
            <>
              <span className="cabecalho__usuario">Olá, {usuario.nome.split(' ')[0]}</span>
              <button type="button" className="botao botao--claro" onClick={() => navegar('/sair')}>
                Sair
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="botao botao--claro">
                Entrar
              </Link>
              <Link to="/cadastro" className="botao botao--primario">
                Criar conta
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
