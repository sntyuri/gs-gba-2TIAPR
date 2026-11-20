import { Link } from 'react-router-dom';
import { useTituloPagina } from '../hooks/useTituloPagina.js';

export default function NaoEncontrada() {
  useTituloPagina('Página não encontrada');

  return (
    <div className="conteiner conteiner--estreito secao">
      <h1>Esta página não existe</h1>
      <p>O endereço pode ter sido digitado errado ou a página mudou de lugar.</p>
      <Link to="/" className="botao botao--primario">
        Ir para o início
      </Link>
    </div>
  );
}
