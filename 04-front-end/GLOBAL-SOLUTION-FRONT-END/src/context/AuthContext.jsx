import { createContext, useContext, useMemo, useState } from 'react';
import {
  autenticar,
  cadastrarUsuario,
  encerrarSessao,
  excluirUsuario,
  obterUsuarioDaSessao,
} from '../services/auth.js';
import { excluirSolicitacoesDoUsuario } from '../services/solicitacoes.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Estado inicial lido da sessão: recarregar a página não derruba o login.
  const [usuario, setUsuario] = useState(() => obterUsuarioDaSessao());

  const valor = useMemo(
    () => ({
      usuario,
      async entrar(email, senha) {
        const encontrado = await autenticar(email, senha);
        if (encontrado) setUsuario(encontrado);
        return Boolean(encontrado);
      },
      async cadastrar(dados) {
        setUsuario(await cadastrarUsuario(dados));
      },
      sair() {
        encerrarSessao();
        setUsuario(null);
      },
      excluirConta() {
        if (!usuario) return;
        excluirSolicitacoesDoUsuario(usuario.id);
        excluirUsuario(usuario.id);
        setUsuario(null);
      },
    }),
    [usuario],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error('useAuth precisa estar dentro de <AuthProvider>.');
  return contexto;
}
