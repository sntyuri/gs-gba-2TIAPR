import { useEffect, useState } from 'react';
import { ler, gravar } from '../services/storage.js';

// Preferências de leitura (letra maior e alto contraste), lembradas no navegador.
export function usePreferencias() {
  const [preferencias, setPreferencias] = useState(() =>
    ler('preferencias', { letraMaior: false, altoContraste: false }),
  );

  useEffect(() => {
    const raiz = document.documentElement;
    raiz.dataset.letra = preferencias.letraMaior ? 'maior' : 'padrao';
    raiz.dataset.contraste = preferencias.altoContraste ? 'alto' : 'padrao';
    gravar('preferencias', preferencias);
  }, [preferencias]);

  const alternar = (chave) =>
    setPreferencias((atual) => ({ ...atual, [chave]: !atual[chave] }));

  return { preferencias, alternar };
}
