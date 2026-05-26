import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import POS from './pages/POS';
import Clientes from './pages/Clientes';
import Productos from './pages/Productos';
import Historial from './pages/Historial';
import Configuracion from './pages/Configuracion';
import Fiados from './pages/Fiados';
import Verificacion from './pages/Verificacion';
import SuperAdmin from './pages/SuperAdmin';
import Registrarse from './pages/Registrarse';
import { CompanyProvider } from './contexts/CompanyContext';
import { pingSunatApi } from './lib/sunatService';
import { useEffect } from 'react';

function App() {
  useEffect(() => {
    // Ping al servidor de facturación (Render) para evitar el Cold-Starttttt
    pingSunatApi();
  }, []);

  return (
    <AuthProvider>
      <CompanyProvider>
        <Router>
          <Routes>
            {/* Ruta pública: Login */}
            <Route path="/login" element={<Login />} />

            {/* Rutas protegidas: Solo usuarios autenticados */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/pos" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="pos" element={<POS />} />
              <Route path="clientes" element={<Clientes />} />
              <Route path="productos" element={<Productos />} />
              <Route path="historial" element={<Historial />} />
              <Route path="fiados" element={<Fiados />} />
              <Route path="configuracion" element={<Configuracion />} />
              <Route path="superadmin" element={<SuperAdmin />} />
            </Route>

            {/* Rutas públicas */}
            <Route path="/verificacion" element={<Verificacion />} />
            <Route path="/registrarse" element={<Registrarse />} />

            {/* Cualquier otra ruta → Login */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Router>
      </CompanyProvider>
    </AuthProvider>
  );
}

export default App;