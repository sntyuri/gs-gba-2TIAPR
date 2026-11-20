import Aviso from './Aviso.jsx';
import { SeloPrioridade } from './Selos.jsx';

const EMERGENCIAS = [
  { numero: '193', nome: 'Bombeiros' },
  { numero: '199', nome: 'Defesa Civil' },
  { numero: '192', nome: 'SAMU' },
  { numero: '190', nome: 'Polícia Militar' },
];

// Mostra o que a IA entendeu, o que vai acontecer e por quê.
// `nivelTitulo` permite usar o componente em páginas com hierarquias diferentes.
export default function RespostaIA({ analise, nivelTitulo = 2 }) {
  const Titulo = `h${nivelTitulo}`;
  const Subtitulo = `h${nivelTitulo + 1}`;

  return (
    <section className="resposta-ia" aria-label="Resultado da triagem por IA">
      <header className="resposta-ia__topo">
        <Titulo>{analise.titulo}</Titulo>
        <SeloPrioridade nivel={analise.prioridade} />
      </header>

      {analise.emergencia && (
        <Aviso tipo="perigo" titulo="Se alguém corre perigo agora, ligue antes de registrar">
          <p>Este registro não substitui o atendimento de emergência.</p>
          <ul className="emergencias">
            {EMERGENCIAS.map((item) => (
              <li key={item.numero}>
                <a href={`tel:${item.numero}`}>
                  <strong>{item.numero}</strong> {item.nome}
                </a>
              </li>
            ))}
          </ul>
        </Aviso>
      )}

      <p className="resposta-ia__texto">{analise.resposta}</p>

      <dl className="encaminhamento">
        <div>
          <dt>Tipo de problema</dt>
          <dd>{analise.categoriaNome}</dd>
        </div>
        <div>
          <dt>Órgão responsável</dt>
          <dd>{analise.orgao}</dd>
        </div>
        <div>
          <dt>Previsão de resposta</dt>
          <dd>{analise.prazoTexto}</dd>
        </div>
      </dl>

      {analise.revisaoHumana && (
        <Aviso tipo="atencao" titulo="Uma pessoa vai conferir esta classificação">
          <p>
            A IA não teve certeza suficiente. Em vez de arriscar um encaminhamento errado, o pedido
            passa antes por conferência humana.
          </p>
        </Aviso>
      )}

      <div className="resposta-ia__colunas">
        <div>
          <Subtitulo>O que acontece agora</Subtitulo>
          <ol>
            {analise.proximosPassos.map((passo) => (
              <li key={passo}>{passo}</li>
            ))}
          </ol>
        </div>
        <div>
          <Subtitulo>Enquanto isso</Subtitulo>
          <ul>
            {analise.orientacoes.map((orientacao) => (
              <li key={orientacao}>{orientacao}</li>
            ))}
          </ul>
        </div>
      </div>

      <details className="explicacao">
        <summary>Por que a IA chegou a este resultado?</summary>
        <div className="explicacao__corpo">
          {analise.corrigidaPeloCidadao ? (
            <p>A categoria foi definida por você. A IA recalculou a prioridade, o órgão e o prazo.</p>
          ) : analise.termos.length > 0 ? (
            <p>
              Trechos do seu relato que indicaram o tipo de problema:{' '}
              {analise.termos.map((termo) => (
                <mark key={termo}>{termo}</mark>
              ))}
            </p>
          ) : (
            <p>Nenhum trecho do relato indicou com clareza um tipo de problema conhecido.</p>
          )}

          {analise.sinais.length > 0 ? (
            <>
              <p>Sinais que pesaram na prioridade:</p>
              <ul>
                {analise.sinais.map((sinal) => (
                  <li key={sinal.id}>
                    {sinal.rotulo}:{' '}
                    {sinal.trechos.map((trecho) => (
                      <mark key={trecho}>{trecho}</mark>
                    ))}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p>Nenhum sinal de risco, urgência ou longa duração foi encontrado no relato.</p>
          )}

          {analise.confianca !== null && (
            <p>
              Grau de certeza da classificação: <strong>{analise.confianca}%</strong>. Abaixo de
              55%, o pedido passa por conferência humana.
            </p>
          )}
          <p className="texto-suave">
            Esta triagem é feita por uma IA simulada (regras e pesos) que roda no seu navegador: o
            relato não é enviado a nenhum servidor. Ela pode errar, e você pode corrigir a categoria
            na página da solicitação.
          </p>
        </div>
      </details>
    </section>
  );
}
