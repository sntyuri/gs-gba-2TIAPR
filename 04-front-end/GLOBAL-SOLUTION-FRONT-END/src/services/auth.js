// Login local: as contas ficam apenas no navegador (localStorage).
//
// Cuidados adotados mesmo sendo um protótipo:
//   - a senha nunca é gravada em texto puro: guardamos um hash com "sal";
//   - a sessão fica em sessionStorage e termina quando a aba é fechada;
//   - pedimos o mínimo de dados (nome e e-mail), sem CPF ou endereço.
//
// Em produção, autenticação é responsabilidade de um backend.

import { ler, gravar, gerarId } from './storage.js';

const CHAVE_USUARIOS = 'usuarios';
const CHAVE_SESSAO = 'zela:sessao';
const ITERACOES = 150000;

const paraHex = (buffer) =>
  Array.from(new Uint8Array(buffer), (byte) => byte.toString(16).padStart(2, '0')).join('');

function gerarSal() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return paraHex(bytes);
}

// crypto.subtle só existe em contexto seguro (https ou localhost).
const algoritmoDisponivel = () => (globalThis.crypto?.subtle ? 'PBKDF2-SHA256' : 'DEMO-FRACO');

async function derivarHash(senha, sal, algoritmo) {
  if (algoritmo === 'PBKDF2-SHA256') {
    const codificador = new TextEncoder();
    const chave = await crypto.subtle.importKey('raw', codificador.encode(senha), 'PBKDF2', false, [
      'deriveBits',
    ]);
    const bits = await crypto.subtle.deriveBits(
      { name: 'PBKDF2', hash: 'SHA-256', salt: codificador.encode(sal), iterations: ITERACOES },
      chave,
      256,
    );
    return paraHex(bits);
  }
  // Reserva para quando o protótipo é aberto por http em outro aparelho da rede.
  // Não é seguro: serve apenas para a demonstração não parar.
  let hash = 5381;
  const texto = sal + senha;
  for (let i = 0; i < texto.length; i += 1) hash = ((hash << 5) + hash) ^ texto.charCodeAt(i);
  return (hash >>> 0).toString(16);
}

const listarUsuarios = () => ler(CHAVE_USUARIOS, []);
const normalizarEmail = (email) => String(email ?? '').trim().toLowerCase();

// Nunca devolvemos o hash da senha para as telas.
function semSenha(usuario) {
  if (!usuario) return null;
  const { senha: _senha, ...publico } = usuario;
  return publico;
}

export const emailValido = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizarEmail(email));

export async function cadastrarUsuario({ nome, email, senha }) {
  const usuarios = listarUsuarios();
  const emailLimpo = normalizarEmail(email);

  if (usuarios.some((usuario) => usuario.email === emailLimpo)) {
    throw new Error('Já existe uma conta com este e-mail neste navegador. Entre com ela ou use outro e-mail.');
  }

  const algoritmo = algoritmoDisponivel();
  const sal = gerarSal();
  const agora = new Date().toISOString();
  const novo = {
    id: gerarId(),
    nome: nome.trim(),
    email: emailLimpo,
    senha: { algoritmo, sal, hash: await derivarHash(senha, sal, algoritmo) },
    criadoEm: agora,
    consentimentoEm: agora,
  };

  if (!gravar(CHAVE_USUARIOS, [...usuarios, novo])) {
    throw new Error('Não foi possível salvar a conta. Verifique se o navegador permite armazenamento local.');
  }
  iniciarSessao(novo.id);
  return semSenha(novo);
}

export async function autenticar(email, senha) {
  const usuario = listarUsuarios().find((item) => item.email === normalizarEmail(email));
  // Mesma mensagem para e-mail inexistente e senha errada: não revelamos quem tem conta.
  if (!usuario) return null;
  const hash = await derivarHash(senha, usuario.senha.sal, usuario.senha.algoritmo);
  if (hash !== usuario.senha.hash) return null;
  iniciarSessao(usuario.id);
  return semSenha(usuario);
}

function iniciarSessao(usuarioId) {
  try {
    sessionStorage.setItem(CHAVE_SESSAO, usuarioId);
  } catch {
    // Sem sessionStorage a sessão vale só enquanto a página estiver aberta.
  }
}

export function encerrarSessao() {
  try {
    sessionStorage.removeItem(CHAVE_SESSAO);
  } catch {
    // nada a limpar
  }
}

export function obterUsuarioDaSessao() {
  try {
    const id = sessionStorage.getItem(CHAVE_SESSAO);
    if (!id) return null;
    return semSenha(listarUsuarios().find((usuario) => usuario.id === id));
  } catch {
    return null;
  }
}

export function excluirUsuario(usuarioId) {
  gravar(
    CHAVE_USUARIOS,
    listarUsuarios().filter((usuario) => usuario.id !== usuarioId),
  );
  encerrarSessao();
}
