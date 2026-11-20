import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import Aviso from '../components/Aviso.jsx';
import Campo from '../components/Campo.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useTituloPagina } from '../hooks/useTituloPagina.js';
import { emailValido } from '../services/auth.js';

const INICIAL = { nome: '', email: '', senha: '', confirmacao: '', consentimento: false };

function validar(dados) {
  const erros = {};
  if (dados.nome.trim().length < 2) erros.nome = 'Informe como você quer ser chamado.';
  if (!emailValido(dados.email)) erros.email = 'Informe um e-mail válido, como nome@exemplo.com.';
  if (dados.senha.length < 8) erros.senha = 'A senha precisa ter pelo menos 8 caracteres.';
  if (dados.confirmacao !== dados.senha) erros.confirmacao = 'As duas senhas precisam ser iguais.';
  if (!dados.consentimento) erros.consentimento = 'Marque a caixa para autorizar o uso dos dados.';
  return erros;
}

export default function Cadastro() {
  useTituloPagina('Criar conta');
  const { usuario, cadastrar } = useAuth();
  const navegar = useNavigate();
  const [dados, setDados] = useState(INICIAL);
  const [erros, setErros] = useState({});
  const [erroGeral, setErroGeral] = useState('');
  const [enviando, setEnviando] = useState(false);

  if (usuario && !enviando) return <Navigate to="/painel" replace />;

  function aoMudar(evento) {
    const { name, value, type, checked } = evento.target;
    setDados((atual) => ({ ...atual, [name]: type === 'checkbox' ? checked : value }));
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    const encontrados = validar(dados);
    setErros(encontrados);
    setErroGeral('');

    const primeiroComErro = Object.keys(encontrados)[0];
    if (primeiroComErro) {
      // Leva o foco ao primeiro campo com problema.
      document.getElementById(primeiroComErro)?.focus();
      return;
    }

    setEnviando(true);
    try {
      await cadastrar(dados);
      navegar('/painel', { replace: true, state: { boasVindas: true } });
    } catch (falha) {
      setErroGeral(falha.message);
      setEnviando(false);
    }
  }

  return (
    <div className="conteiner conteiner--estreito secao">
      <h1>Criar conta</h1>
      <p>Pedimos só o necessário para você acompanhar seus pedidos: nome e e-mail.</p>

      {erroGeral && (
        <Aviso tipo="perigo" anunciar>
          <p>{erroGeral}</p>
        </Aviso>
      )}

      <form onSubmit={aoEnviar} noValidate className="formulario">
        <Campo
          id="nome"
          rotulo="Nome"
          autoComplete="name"
          value={dados.nome}
          onChange={aoMudar}
          erro={erros.nome}
        />
        <Campo
          id="email"
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          value={dados.email}
          onChange={aoMudar}
          erro={erros.email}
        />
        <Campo
          id="senha"
          rotulo="Senha"
          dica="Pelo menos 8 caracteres."
          type="password"
          autoComplete="new-password"
          value={dados.senha}
          onChange={aoMudar}
          erro={erros.senha}
        />
        <Campo
          id="confirmacao"
          rotulo="Repita a senha"
          type="password"
          autoComplete="new-password"
          value={dados.confirmacao}
          onChange={aoMudar}
          erro={erros.confirmacao}
        />

        <div className={`campo campo--caixa${erros.consentimento ? ' campo--erro' : ''}`}>
          <input
            id="consentimento"
            name="consentimento"
            type="checkbox"
            checked={dados.consentimento}
            onChange={aoMudar}
            aria-invalid={erros.consentimento ? 'true' : undefined}
            aria-describedby={erros.consentimento ? 'consentimento-erro' : undefined}
          />
          <label htmlFor="consentimento">
            Autorizo guardar meu nome, e-mail e minhas solicitações neste navegador para registrar e
            acompanhar pedidos, como explicado em <Link to="/privacidade">Privacidade</Link>.
          </label>
          {erros.consentimento && (
            <p id="consentimento-erro" className="campo__erro">
              {erros.consentimento}
            </p>
          )}
        </div>

        <button type="submit" className="botao botao--primario" disabled={enviando}>
          {enviando ? 'Criando conta…' : 'Criar conta'}
        </button>
      </form>

      <p>
        Já tem conta? <Link to="/login">Entrar</Link>
      </p>
    </div>
  );
}
