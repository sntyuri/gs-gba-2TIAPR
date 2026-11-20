import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

// Envolve as rotas que exigem login. Sem sessão, manda para /login
// e guarda o endereço pedido para voltar depois de entrar.
export default function RotaProtegida() {
  const { usuario } = useAuth();
  const local = useLocation();

  if (!usuario) {
    return <Navigate to="/login" replace state={{ de: local.pathname }} />;
  }
  return <Outlet />;
}
