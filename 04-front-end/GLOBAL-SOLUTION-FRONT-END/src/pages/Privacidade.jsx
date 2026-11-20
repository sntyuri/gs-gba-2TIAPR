import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Aviso from '../components/Aviso.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useTituloPagina } from '../hooks/useTituloPagina.js';
import { formatarDataHora } from '../services/formato.js';
import { listarSolicitacoes } from '../services/solicitacoes.js';

export default function Privacidade() {
  useTituloPagina('Privacidade');
  const { usuario, excluirConta } = useAuth();
  const navegar = useNavigate();
  const [confirmando, setConfirmando] = useState(false);
  const [baixado, setBaixado] = useState(false);

  // Direito de acesso e portabilidade: o cidadão leva uma cópia dos seus dados.
  function aoBaixar() {
    const copia = {
      exportadoEm: new Date().toISOString(),
      conta: {
        nome: usuario.nome,
        email: usuario.email,
        criadaEm: usuario.criadoEm,
        consentimentoEm: usuario.consentimentoEm,
      },
      solicitacoes: listarSolicitacoes(usuario.id).map(({ usuarioId: _usuarioId, ...resto }) => resto),
    };
    const arquivo = new Blob([JSON.stringify(copia, null, 2)], { type: 'application/json' });
    const endereco = URL.createObjectURL(arquivo);
    const link = document.createElement('a');
    link.href = endereco;
    link.download = 'meus-dados-zela.json';
    link.click();
    URL.revokeObjectURL(endereco);
    setBaixado(true);
  }

  // Direito de eliminação: apaga a conta e todos os pedidos deste navegador.
  function aoExcluir() {
    excluirConta();
    navegar('/', { replace: true });
  }

  return (
    <div className="conteiner conteiner--medio secao texto-corrido">
      <h1>Privacidade</h1>
      <p>
        A Zela foi pensada para funcionar com o mínimo de dados pessoais, seguindo os princípios da
        Lei Geral de Proteção de Dados (LGPD): finalidade, necessidade e transparência.
      </p>

      <h2>O que guardamos e para quê</h2>
      <table className="tabela">
        <thead>
          <tr>
            <th scope="col">Dado</th>
            <th scope="col">Para que serve</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Nome e e-mail</th>
            <td>Identificar a sua conta e separar os seus pedidos dos de outras pessoas.</td>
          </tr>
          <tr>
            <th scope="row">Senha</th>
            <td>Proteger a conta. É guardada embaralhada (hash com sal), nunca em texto legível.</td>
          </tr>
          <tr>
            <th scope="row">Relato, bairro e ponto de referência</th>
            <td>Classificar o problema e indicar o órgão responsável.</td>
          </tr>
          <tr>
            <th scope="row">Ajustes de leitura</th>
            <td>Lembrar se você prefere letra maior ou alto contraste.</td>
          </tr>
        </tbody>
      </table>

      <h2>O que não pedimos</h2>
      <p>
        CPF, telefone, endereço residencial e localização do aparelho não são necessários e não são
        pedidos. Se você escrever CPF, telefone ou e-mail no relato, eles são trocados por um aviso
        de remoção antes da análise e antes de salvar.
      </p>

      <h2>Onde os dados ficam</h2>
      <p>
        Apenas neste navegador (armazenamento local). Nada é enviado a servidores: a IA de triagem
        roda no seu próprio aparelho e o site não usa cookies de rastreamento nem fontes ou scripts
        de terceiros. A sessão termina quando você fecha a aba.
      </p>
      <p>
        Em um computador compartilhado, outras pessoas com acesso ao navegador podem ver os dados
        guardados. Nesse caso, saia da conta ao terminar e, se preferir, exclua os dados abaixo.
      </p>

      <h2>Decisões automatizadas</h2>
      <p>
        A classificação é feita por IA e sempre vem acompanhada da explicação. Quando a IA tem pouca
        certeza, o pedido passa por conferência humana, e você pode corrigir a categoria a qualquer
        momento.
      </p>

      <h2>Seus dados, suas escolhas</h2>
      {usuario ? (
        <>
          <p>
            Conta de <strong>{usuario.nome}</strong> ({usuario.email}). Autorização registrada em{' '}
            {formatarDataHora(usuario.consentimentoEm)}.
          </p>
          <div role="status">
            {baixado && (
              <Aviso tipo="sucesso">
                <p>Cópia gerada: confira o arquivo meus-dados-zela.json nos seus downloads.</p>
              </Aviso>
            )}
          </div>
          <div className="acoes">
            <button type="button" className="botao botao--secundario" onClick={aoBaixar}>
              Baixar meus dados
            </button>
            {confirmando ? (
              <span className="confirmacao" role="group" aria-label="Confirmar exclusão da conta">
                <span>Isso apaga a conta e todos os pedidos. Não dá para desfazer.</span>
                <button type="button" className="botao botao--perigo" onClick={aoExcluir}>
                  Excluir conta e dados
                </button>
                <button type="button" className="botao botao--secundario" onClick={() => setConfirmando(false)}>
                  Manter conta
                </button>
              </span>
            ) : (
              <button type="button" className="botao botao--secundario" onClick={() => setConfirmando(true)}>
                Excluir conta e dados
              </button>
            )}
          </div>
        </>
      ) : (
        <p>
          <Link to="/login">Entre na sua conta</Link> para baixar uma cópia dos seus dados ou excluir
          a conta.
        </p>
      )}
    </div>
  );
}
