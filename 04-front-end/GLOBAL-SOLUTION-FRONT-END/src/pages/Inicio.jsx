import { Link } from 'react-router-dom';
import TesteTriagem from '../components/TesteTriagem.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useTituloPagina } from '../hooks/useTituloPagina.js';

export default function Inicio() {
  useTituloPagina('Início');
  const { usuario } = useAuth();
  const destino = usuario ? '/solicitacoes/nova' : '/cadastro';

  return (
    <>
      <section className="abertura">
        <div className="conteiner abertura__grade">
          <div className="abertura__texto">
            <h1>Viu um problema na sua rua? Conte com as suas palavras.</h1>
            <p className="abertura__apoio">
              Você não precisa saber qual secretaria cuida de quê. A Zela lê o seu relato, identifica
              o tipo de problema, define a prioridade e indica o órgão responsável. Depois, você
              acompanha tudo pelo protocolo.
            </p>
            <p>
              <Link to={destino} className="botao botao--primario">
                {usuario ? 'Registrar uma solicitação' : 'Criar conta e registrar'}
              </Link>
            </p>
          </div>

          <div className="abertura__teste">
            <TesteTriagem destino={destino} />
          </div>
        </div>
      </section>

      <section className="conteiner secao">
        <h2>Como funciona</h2>
        <ol className="passos">
          <li>
            <h3>Você descreve</h3>
            <p>Escreva do seu jeito: o que está acontecendo, onde e desde quando.</p>
          </li>
          <li>
            <h3>A IA faz a triagem</h3>
            <p>
              Ela classifica o problema, avalia a urgência e mostra quais trechos do seu relato
              pesaram na decisão.
            </p>
          </li>
          <li>
            <h3>O pedido chega ao órgão certo</h3>
            <p>
              Você recebe um protocolo, um prazo estimado e orientações de segurança, e acompanha
              cada etapa.
            </p>
          </li>
        </ol>
      </section>

      <section className="conteiner secao secao--duas">
        <div>
          <h2>Seus dados ficam com você</h2>
          <p>
            A conta pede só nome e e-mail. Se você escrever CPF, telefone ou e-mail no relato, eles
            são removidos antes de salvar. Tudo fica guardado apenas neste navegador, e você pode
            baixar ou apagar quando quiser.
          </p>
          <p>
            <Link to="/privacidade">Como a Zela trata seus dados</Link>
          </p>
        </div>
        <div>
          <h2>Uma cidade que responde</h2>
          <p>
            O projeto apoia os Objetivos de Desenvolvimento Sustentável 11 (cidades e comunidades
            sustentáveis) e 16 (instituições eficazes), aproximando o cidadão do serviço público.
          </p>
          <p>
            <Link to="/sobre">Problema, público e ODS</Link>
          </p>
        </div>
      </section>
    </>
  );
}
