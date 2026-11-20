import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Aviso from '../components/Aviso.jsx';
import Campo from '../components/Campo.jsx';
import RespostaIA from '../components/RespostaIA.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { EXEMPLOS } from '../data/exemplos.js';
import { useTituloPagina } from '../hooks/useTituloPagina.js';
import { analisarSolicitacao } from '../services/ia.js';
import { mascararDadosPessoais, resumirRemocoes } from '../services/privacidade.js';
import { criarSolicitacao } from '../services/solicitacoes.js';

const LIMITE = 600;
const INICIAL = { descricao: '', bairro: '', referencia: '' };

function validar(dados) {
  const erros = {};
  if (dados.descricao.trim().length < 15) {
    erros.descricao = 'Conte um pouco mais: o que está acontecendo e onde (mínimo de 15 caracteres).';
  }
  if (dados.bairro.trim().length < 2) erros.bairro = 'Informe o bairro para direcionar a equipe.';
  return erros;
}

export default function NovaSolicitacao() {
  useTituloPagina('Nova solicitação');
  const { usuario } = useAuth();
  const navegar = useNavigate();

  const [dados, setDados] = useState(INICIAL);
  const [erros, setErros] = useState({});
  const [etapa, setEtapa] = useState('formulario'); // formulario | analisando | resultado
  const [previa, setPrevia] = useState(null); // { descricao, referencia, removidos, analise }
  const [erroGeral, setErroGeral] = useState('');

  const montado = useRef(true);
  const tituloResultado = useRef(null);

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  // Quando a triagem termina, o foco vai para o resultado.
  useEffect(() => {
    if (etapa === 'resultado') tituloResultado.current?.focus();
  }, [etapa]);

  function aoMudar(evento) {
    const { name, value } = evento.target;
    setDados((atual) => ({ ...atual, [name]: value }));
  }

  async function aoAnalisar(evento) {
    evento.preventDefault();
    const encontrados = validar(dados);
    setErros(encontrados);
    const primeiroComErro = Object.keys(encontrados)[0];
    if (primeiroComErro) {
      document.getElementById(primeiroComErro)?.focus();
      return;
    }

    setEtapa('analisando');

    // 1) Proteção de dados: remove dados pessoais ANTES de analisar e salvar.
    const descricao = mascararDadosPessoais(dados.descricao.trim());
    const referencia = mascararDadosPessoais(dados.referencia.trim());

    // 2) Processamento inteligente do relato já protegido.
    const analise = await analisarSolicitacao(descricao.texto, { bairro: dados.bairro });
    if (!montado.current) return;

    setPrevia({
      descricao: descricao.texto,
      referencia: referencia.texto,
      removidos: [...descricao.encontrados, ...referencia.encontrados],
      analise,
    });
    setEtapa('resultado');
  }

  function aoRegistrar() {
    try {
      const nova = criarSolicitacao({
        usuarioId: usuario.id,
        descricao: previa.descricao,
        bairro: dados.bairro,
        referencia: previa.referencia,
        analise: previa.analise,
      });
      navegar(`/solicitacoes/${nova.id}`, { state: { recemCriada: true } });
    } catch (falha) {
      setErroGeral(falha.message);
    }
  }

  if (etapa === 'resultado' && previa) {
    return (
      <div className="conteiner conteiner--medio secao">
        <h1 ref={tituloResultado} tabIndex={-1}>
          Confira a triagem antes de registrar
        </h1>

        {erroGeral && (
          <Aviso tipo="perigo" anunciar>
            <p>{erroGeral}</p>
          </Aviso>
        )}

        {previa.removidos.length > 0 && (
          <Aviso tipo="info" titulo="Removemos dados pessoais do seu relato">
            <p>
              Encontramos {resumirRemocoes(previa.removidos)}. Esses dados não são necessários para
              resolver o problema e não serão salvos.
            </p>
          </Aviso>
        )}

        <section className="relato">
          <h2>Seu relato, como será salvo</h2>
          <blockquote>{previa.descricao}</blockquote>
          <p className="texto-suave">
            Bairro: {dados.bairro.trim()}
            {previa.referencia && `. Ponto de referência: ${previa.referencia}`}
          </p>
        </section>

        <RespostaIA analise={previa.analise} nivelTitulo={2} />

        <div className="acoes">
          <button type="button" className="botao botao--primario" onClick={aoRegistrar}>
            Registrar solicitação
          </button>
          <button type="button" className="botao botao--secundario" onClick={() => setEtapa('formulario')}>
            Voltar e editar o relato
          </button>
        </div>
      </div>
    );
  }

  const analisando = etapa === 'analisando';
  const restantes = LIMITE - dados.descricao.length;

  return (
    <div className="conteiner conteiner--medio secao">
      <h1>Nova solicitação</h1>
      <p>
        Escreva como você contaria para um vizinho. A IA identifica o tipo de problema e a urgência;
        você confere antes de registrar.
      </p>

      <form onSubmit={aoAnalisar} noValidate className="formulario">
        <Campo
          id="descricao"
          rotulo="O que está acontecendo?"
          dica="Diga o que é, onde fica e desde quando. Não inclua CPF, telefone nem nome de outras pessoas."
          multilinha
          rows={6}
          maxLength={LIMITE}
          value={dados.descricao}
          onChange={aoMudar}
          erro={erros.descricao}
        />
        <p className="contador" aria-hidden="true">
          {restantes} caracteres restantes
        </p>

        <div className="exemplos">
          <span id="rotulo-exemplos-nova">Para testar, use um exemplo:</span>
          <ul aria-labelledby="rotulo-exemplos-nova">
            {EXEMPLOS.map((exemplo) => (
              <li key={exemplo.rotulo}>
                <button
                  type="button"
                  className="exemplo"
                  onClick={() => setDados((atual) => ({ ...atual, descricao: exemplo.texto }))}
                >
                  {exemplo.rotulo}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <Campo
          id="bairro"
          rotulo="Bairro"
          autoComplete="address-level3"
          value={dados.bairro}
          onChange={aoMudar}
          erro={erros.bairro}
        />
        <Campo
          id="referencia"
          rotulo="Ponto de referência"
          opcional
          dica="Ex.: em frente à padaria, esquina com a rua do mercado. Não precisa ser o seu endereço."
          value={dados.referencia}
          onChange={aoMudar}
        />

        <button type="submit" className="botao botao--primario" disabled={analisando}>
          {analisando ? 'Analisando o relato…' : 'Analisar pedido'}
        </button>
      </form>

      <p className="so-leitor" role="status">
        {analisando && 'A IA está analisando o seu relato.'}
      </p>
    </div>
  );
}
