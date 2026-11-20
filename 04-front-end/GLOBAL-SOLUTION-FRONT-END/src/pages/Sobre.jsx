import { useTituloPagina } from '../hooks/useTituloPagina.js';

const ODS = [
  {
    numero: 11,
    nome: 'Cidades e comunidades sustentáveis',
    relacao:
      'Facilita o registro de problemas de iluminação, resíduos, drenagem, calçadas e áreas verdes, que afetam a segurança e a qualidade dos espaços públicos.',
  },
  {
    numero: 16,
    nome: 'Paz, justiça e instituições eficazes',
    relacao:
      'Torna o atendimento mais transparente: o cidadão vê para onde o pedido foi, por quê, e em que etapa está.',
  },
  {
    numero: 10,
    nome: 'Redução das desigualdades',
    relacao:
      'Linguagem simples e interface acessível permitem que pessoas com menos familiaridade com serviços digitais, idosos e pessoas com deficiência também sejam atendidos.',
  },
];

export default function Sobre() {
  useTituloPagina('Sobre o projeto');

  return (
    <div className="conteiner conteiner--medio secao texto-corrido">
      <h1>Sobre o projeto</h1>

      <h2>O problema</h2>
      <p>
        Quando aparece um buraco, um poste apagado ou um bueiro entupido, o cidadão precisa
        descobrir sozinho qual órgão procurar e como descrever o problema. Um pedido aberto no canal
        errado precisa ser reencaminhado, e um caso urgente pode ficar na mesma fila de um caso
        simples. Essa dificuldade desestimula o registro.
      </p>

      <h2>Quem é afetado</h2>
      <p>
        Moradores de áreas urbanas que dependem da zeladoria pública no dia a dia. O protótipo dá
        atenção especial a idosos, pessoas com deficiência e pessoas com pouca familiaridade com
        serviços digitais, que têm mais dificuldade com formulários longos e linguagem técnica.
      </p>

      <h2>A solução</h2>
      <p>
        O cidadão descreve o problema com as próprias palavras. Uma IA de triagem identifica o tipo
        de problema, calcula a prioridade a partir de sinais de risco, indica o órgão responsável e
        o prazo estimado, e devolve uma resposta em linguagem simples com orientações de segurança.
        O pedido ganha um protocolo e pode ser acompanhado etapa por etapa.
      </p>

      <h2>Como a IA decide</h2>
      <p>
        Neste protótipo a IA é simulada: um classificador por regras e pesos, executado no
        navegador. Ele procura no relato termos ligados a cada tipo de problema e sinais que
        aumentam a prioridade, como risco imediato, presença de crianças ou idosos, quantidade de
        pessoas afetadas e duração do problema.
      </p>
      <ul>
        <li>Toda resposta mostra os trechos do relato que pesaram na decisão.</li>
        <li>Com grau de certeza baixo, o pedido passa por conferência humana.</li>
        <li>O cidadão pode corrigir a categoria, e o encaminhamento é refeito.</li>
        <li>Diante de risco imediato, os telefones de emergência aparecem antes de tudo.</li>
      </ul>

      <h2>Objetivos de Desenvolvimento Sustentável</h2>
      <ul className="ods">
        {ODS.map((item) => (
          <li key={item.numero}>
            <h3>
              ODS {item.numero}: {item.nome}
            </h3>
            <p>{item.relacao}</p>
          </li>
        ))}
      </ul>

      <h2>Limites do protótipo</h2>
      <p>
        Os órgãos e prazos são ilustrativos e nenhum pedido é enviado a uma prefeitura real. Os
        dados ficam apenas no navegador, e o login local serve para demonstração: em produção, a
        autenticação e o armazenamento ficariam em um servidor seguro.
      </p>
    </div>
  );
}
