// Proteção de dados pessoais (LGPD): antes de salvar ou analisar um relato,
// removemos dados que identificam pessoas e que não são necessários para
// resolver o problema (minimização de dados).

const PADRAO_EMAIL = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g;
const PADRAO_CPF_PONTUADO = /\b\d{3}\.\d{3}\.\d{3}-?\d{2}\b/g;
const PADRAO_ONZE_DIGITOS = /\b\d{11}\b/g;
const PADRAO_TELEFONE =
  /(?:\+?55[\s-]?)?(?:\(\d{2}\)|\b\d{2})?[\s-]?\b9?\d{4}[\s-]?\d{4}\b/g;

// Confere os dois dígitos verificadores do CPF.
export function cpfValido(valor) {
  const d = String(valor).replace(/\D/g, '');
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  const digito = (tamanho) => {
    let soma = 0;
    for (let i = 0; i < tamanho; i += 1) soma += Number(d[i]) * (tamanho + 1 - i);
    const resto = (soma * 10) % 11;
    return resto === 10 ? 0 : resto;
  };
  return digito(9) === Number(d[9]) && digito(10) === Number(d[10]);
}

const ROTULOS = {
  email: 'e-mail',
  cpf: 'CPF',
  telefone: 'telefone',
};

export function mascararDadosPessoais(textoOriginal) {
  const contagem = { email: 0, cpf: 0, telefone: 0 };
  let texto = String(textoOriginal ?? '');

  texto = texto.replace(PADRAO_EMAIL, () => {
    contagem.email += 1;
    return '[e-mail removido]';
  });

  texto = texto.replace(PADRAO_CPF_PONTUADO, () => {
    contagem.cpf += 1;
    return '[CPF removido]';
  });

  // 11 dígitos seguidos podem ser CPF ou celular com DDD: decide pelo dígito verificador.
  texto = texto.replace(PADRAO_ONZE_DIGITOS, (trecho) => {
    if (cpfValido(trecho)) {
      contagem.cpf += 1;
      return '[CPF removido]';
    }
    contagem.telefone += 1;
    return '[telefone removido]';
  });

  texto = texto.replace(PADRAO_TELEFONE, (trecho) => {
    // Menos de 8 dígitos não é telefone (ex.: número de casa, ano).
    if (trecho.replace(/\D/g, '').length < 8) return trecho;
    contagem.telefone += 1;
    const espacoInicial = trecho.match(/^\s*/)[0];
    return `${espacoInicial}[telefone removido]`;
  });

  const encontrados = Object.entries(contagem)
    .filter(([, quantidade]) => quantidade > 0)
    .map(([tipo, quantidade]) => ({ tipo, rotulo: ROTULOS[tipo], quantidade }));

  return {
    texto,
    encontrados,
    total: encontrados.reduce((soma, item) => soma + item.quantidade, 0),
  };
}

export function resumirRemocoes(encontrados) {
  // Soma por tipo (o mesmo dado pode aparecer no relato e no ponto de referência).
  const porTipo = new Map();
  encontrados.forEach((item) => {
    porTipo.set(item.rotulo, (porTipo.get(item.rotulo) ?? 0) + item.quantidade);
  });
  const partes = [...porTipo].map(
    ([rotulo, quantidade]) => `${quantidade} ${rotulo}${quantidade > 1 ? 's' : ''}`,
  );
  if (partes.length <= 1) return partes.join('');
  return `${partes.slice(0, -1).join(', ')} e ${partes.at(-1)}`;
}
