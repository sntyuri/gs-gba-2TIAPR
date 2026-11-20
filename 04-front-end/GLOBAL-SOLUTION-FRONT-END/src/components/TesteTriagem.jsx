import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import RespostaIA from './RespostaIA.jsx';
import { analisarSolicitacao } from '../services/ia.js';
import { mascararDadosPessoais } from '../services/privacidade.js';
import { EXEMPLOS } from '../data/exemplos.js';

// Demonstração aberta na página inicial: o visitante escreve um relato e vê
// a triagem acontecer, sem criar conta. Nada é salvo aqui.
export default function TesteTriagem({ destino }) {
  const [relato, setRelato] = useState('');
  const [situacao, setSituacao] = useState('parado'); // parado | analisando | pronto
  const [analise, setAnalise] = useState(null);
  const [erro, setErro] = useState('');
  const montado = useRef(true);
  const resultado = useRef(null);

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  useEffect(() => {
    if (situacao === 'pronto') resultado.current?.focus();
  }, [situacao]);

  async function aoEnviar(evento) {
    evento.preventDefault();
    if (relato.trim().length < 10) {
      setErro('Escreva pelo menos uma frase contando o que está acontecendo.');
      return;
    }
    setErro('');
    setSituacao('analisando');
    const { texto } = mascararDadosPessoais(relato);
    const resposta = await analisarSolicitacao(texto);
    if (!montado.current) return;
    setAnalise(resposta);
    setSituacao('pronto');
  }

  return (
    <div className="teste-triagem">
      <form onSubmit={aoEnviar} noValidate>
        <label htmlFor="relato-teste">Conte o que está acontecendo</label>
        <textarea
          id="relato-teste"
          rows={4}
          value={relato}
          onChange={(evento) => setRelato(evento.target.value)}
          placeholder="Ex.: O poste em frente à escola está apagado há duas semanas."
          aria-invalid={erro ? 'true' : undefined}
          aria-describedby={erro ? 'relato-teste-erro' : undefined}
        />
        {erro && (
          <p id="relato-teste-erro" className="campo__erro">
            {erro}
          </p>
        )}

        <div className="exemplos">
          <span id="rotulo-exemplos">Ou comece por um exemplo:</span>
          <ul aria-labelledby="rotulo-exemplos">
            {EXEMPLOS.slice(0, 3).map((exemplo) => (
              <li key={exemplo.rotulo}>
                <button type="button" className="exemplo" onClick={() => setRelato(exemplo.texto)}>
                  {exemplo.rotulo}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <button type="submit" className="botao botao--primario" disabled={situacao === 'analisando'}>
          {situacao === 'analisando' ? 'Analisando…' : 'Ver a triagem'}
        </button>
      </form>

      <p className="so-leitor" role="status">
        {situacao === 'analisando' && 'Analisando o relato.'}
        {situacao === 'pronto' && 'Triagem concluída.'}
      </p>

      {situacao === 'pronto' && analise && (
        <div ref={resultado} tabIndex={-1} className="teste-triagem__resultado">
          <RespostaIA analise={analise} nivelTitulo={2} />
          <p className="teste-triagem__proximo">
            Este teste não foi salvo.{' '}
            <Link to={destino}>Registre o pedido para receber um protocolo e acompanhar.</Link>
          </p>
        </div>
      )}
    </div>
  );
}
