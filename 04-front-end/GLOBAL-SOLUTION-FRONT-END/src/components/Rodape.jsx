import { Link } from 'react-router-dom';

export default function Rodape() {
  return (
    <footer className="rodape">
      <div className="conteiner rodape__conteudo">
        <p>
          <strong>Zela é um protótipo acadêmico</strong> da Global Solution 2026.2 da FIAP. Os
          órgãos e prazos são ilustrativos e nenhum pedido é enviado a uma prefeitura real.
        </p>
        <p>
          Seus dados ficam apenas neste navegador. Veja como em{' '}
          <Link to="/privacidade">Privacidade</Link>.
        </p>
      </div>
    </footer>
  );
}
