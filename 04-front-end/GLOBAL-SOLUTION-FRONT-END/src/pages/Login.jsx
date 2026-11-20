import { useRef, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Aviso from '../components/Aviso.jsx';
import Campo from '../components/Campo.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useTituloPagina } from '../hooks/useTituloPagina.js';

export default function Login() {
  useTituloPagina('Entrar');
  const { usuario, entrar } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const destino = local.state?.de ?? '/painel';

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);
  const campoEmail = useRef(null);

  if (usuario) return <Navigate to={destino} replace />;

  async function aoEnviar(evento) {
    evento.preventDefault();
    if (!email.trim() || !senha) {
      setErro('Preencha o e-mail e a senha.');
      return;
    }
    setEnviando(true);
    const entrou = await entrar(email, senha);
    setEnviando(false);
    if (entrou) {
      navegar(destino, { replace: true });
    } else {
      setErro('E-mail ou senha incorretos. Confira os dados e tente de novo.');
      campoEmail.current?.focus();
    }
  }

  return (
    <div className="conteiner conteiner--estreito secao">
      <h1>Entrar</h1>
      {local.state?.de && !erro && (
        <Aviso tipo="info">
          <p>Entre na sua conta para abrir essa página.</p>
        </Aviso>
      )}
      {erro && (
        <Aviso tipo="perigo" anunciar>
          <p>{erro}</p>
        </Aviso>
      )}

      <form onSubmit={aoEnviar} noValidate className="formulario">
        <Campo
          id="email"
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(evento) => setEmail(evento.target.value)}
          ref={campoEmail}
        />
        <Campo
          id="senha"
          rotulo="Senha"
          type="password"
          autoComplete="current-password"
          value={senha}
          onChange={(evento) => setSenha(evento.target.value)}
        />
        <button type="submit" className="botao botao--primario" disabled={enviando}>
          {enviando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>

      <p>
        Ainda não tem conta? <Link to="/cadastro">Criar conta</Link>
      </p>
      <p className="texto-suave">
        A conta existe apenas neste navegador. Se você limpar os dados do navegador, ela é apagada.
      </p>
    </div>
  );
}
