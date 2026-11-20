import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import RotaProtegida from './components/RotaProtegida.jsx';
import Inicio from './pages/Inicio.jsx';
import Login from './pages/Login.jsx';
import Cadastro from './pages/Cadastro.jsx';
import Painel from './pages/Painel.jsx';
import NovaSolicitacao from './pages/NovaSolicitacao.jsx';
import Solicitacoes from './pages/Solicitacoes.jsx';
import DetalheSolicitacao from './pages/DetalheSolicitacao.jsx';
import Privacidade from './pages/Privacidade.jsx';
import Sobre from './pages/Sobre.jsx';
import Sair from './pages/Sair.jsx';
import NaoEncontrada from './pages/NaoEncontrada.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Rotas públicas */}
        <Route path="/" element={<Inicio />} />
        <Route path="/login" element={<Login />} />
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/privacidade" element={<Privacidade />} />
        <Route path="/sobre" element={<Sobre />} />
        <Route path="/sair" element={<Sair />} />

        {/* Rotas que exigem login */}
        <Route element={<RotaProtegida />}>
          <Route path="/painel" element={<Painel />} />
          <Route path="/solicitacoes" element={<Solicitacoes />} />
          <Route path="/solicitacoes/nova" element={<NovaSolicitacao />} />
          <Route path="/solicitacoes/:id" element={<DetalheSolicitacao />} />
        </Route>

        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
