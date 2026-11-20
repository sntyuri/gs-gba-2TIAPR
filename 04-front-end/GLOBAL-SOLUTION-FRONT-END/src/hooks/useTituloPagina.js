import { useEffect } from 'react';

// Cada rota define o título da aba: leitores de tela anunciam a troca de página.
export function useTituloPagina(titulo) {
  useEffect(() => {
    document.title = `${titulo} | Zela`;
  }, [titulo]);
}
