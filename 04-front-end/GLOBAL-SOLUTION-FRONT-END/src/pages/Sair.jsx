import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useTituloPagina } from '../hooks/useTituloPagina.js';

// Rota pública de saída. Encerrar a sessão aqui (e não dentro de uma rota
// protegida) evita que a pessoa seja jogada para a tela de login ao sair.
export default function Sair() {
  useTituloPagina('Saindo');
  const { usuario, sair } = useAuth();

  useEffect(() => {
    if (usuario) sair();
  }, [usuario, sair]);

  if (!usuario) return <Navigate to="/" replace />;
  return (
    <div className="conteiner secao">
      <p role="status">Saindo da conta…</p>
    </div>
  );
}
