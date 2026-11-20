// Acesso ao localStorage em um único lugar.
// Todas as chaves usam o prefixo "zela:" para não misturar com outros sites.

const PREFIXO = 'zela:';

export function ler(chave, padrao) {
  try {
    const bruto = localStorage.getItem(PREFIXO + chave);
    return bruto === null ? padrao : JSON.parse(bruto);
  } catch {
    return padrao;
  }
}

export function gravar(chave, valor) {
  try {
    localStorage.setItem(PREFIXO + chave, JSON.stringify(valor));
    return true;
  } catch {
    // Navegador sem espaço ou com armazenamento bloqueado.
    return false;
  }
}

export function gerarId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
