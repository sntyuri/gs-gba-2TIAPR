import { useEffect, useRef } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Cabecalho from './Cabecalho.jsx';
import Rodape from './Rodape.jsx';

export default function Layout() {
  const { pathname } = useLocation();
  const principal = useRef(null);
  const primeiraRenderizacao = useRef(true);

  // Ao trocar de rota, o foco vai para o conteúdo principal.
  // Sem isso, quem navega por teclado ou leitor de tela fica "preso" no menu.
  useEffect(() => {
    if (primeiraRenderizacao.current) {
      primeiraRenderizacao.current = false;
      return;
    }
    window.scrollTo(0, 0);
    principal.current?.focus();
  }, [pathname]);

  return (
    <>
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>
      <Cabecalho />
      <main id="conteudo" ref={principal} tabIndex={-1} className="principal">
        <Outlet />
      </main>
      <Rodape />
    </>
  );
}
