import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import POS from './pages/POS';
import Clientes from './pages/Clientes';
import Productos from './pages/Productos';
import Historial from './pages/Historial';
import Configuracion from './pages/Configuracion';
import Fiados from './pages/Fiados';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/pos" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="pos" element={<POS />} />
          <Route path="clientes" element={<Clientes />} />
          <Route path="productos" element={<Productos />} />
          <Route path="historial" element={<Historial />} />
          <Route path="fiados" element={<Fiados />} />
          <Route path="configuracion" element={<Configuracion />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;