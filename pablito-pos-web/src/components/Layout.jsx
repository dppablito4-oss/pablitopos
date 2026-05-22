import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { ShoppingCart, Package, Users, FileText, Settings, LayoutDashboard, LogOut, X, Menu } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const Layout = () => {
  const location = useLocation();
  const { user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigation = [
    { name: 'POS (Ventas)', href: '/pos', icon: ShoppingCart },
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Historial', href: '/historial', icon: FileText },
    { name: 'Clientes', href: '/clientes', icon: Users },
    { name: 'Productos', href: '/productos', icon: Package },
    { name: 'Fiados', href: '/fiados', icon: Users },
    { name: 'Configuración', href: '/configuracion', icon: Settings },
  ];

  const NavLinks = ({ onNavigate }) => (
    <>
      {navigation.map((item) => {
        const isActive = location.pathname === item.href;
        return (
          <Link
            key={item.name}
            to={item.href}
            onClick={onNavigate}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              isActive 
                ? 'bg-primary text-primary-content font-medium shadow-sm' 
                : 'text-base-content hover:bg-base-200'
            }`}
          >
            <item.icon size={20} />
            {item.name}
          </Link>
        );
      })}
    </>
  );

  return (
    <div className="flex h-screen bg-base-200">
      {/* Desktop Sidebar */}
      <div className="w-64 bg-base-100 shadow-xl hidden md:flex md:flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary">Pablito POS</h1>
          <p className="text-sm text-base-content/60">Sistema de Ventas</p>
        </div>
        <nav className="flex-1 px-4 space-y-2 overflow-y-auto">
          <NavLinks />
        </nav>
        <div className="p-4 border-t border-base-300 mt-auto space-y-3">
          <div className="flex items-center gap-3">
            <div className="avatar placeholder">
              <div className="bg-primary text-primary-content rounded-full w-10">
                <span className="text-xs font-bold">{user?.email?.substring(0, 2).toUpperCase() || 'US'}</span>
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{user?.email || 'Usuario'}</p>
              <p className="text-xs text-success">● En línea</p>
            </div>
          </div>
          <button
            onClick={signOut}
            className="btn btn-ghost btn-sm w-full justify-start gap-2 text-error hover:bg-error/10"
          >
            <LogOut size={16} /> Cerrar Sesión
          </button>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-72 bg-base-100 shadow-2xl flex flex-col animate-slide-in">
            <div className="p-6 flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-bold text-primary">Pablito POS</h1>
                <p className="text-sm text-base-content/60">Sistema de Ventas</p>
              </div>
              <button className="btn btn-sm btn-circle btn-ghost" onClick={() => setMobileOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <nav className="flex-1 px-4 space-y-2 overflow-y-auto">
              <NavLinks onNavigate={() => setMobileOpen(false)} />
            </nav>
            <div className="p-4 border-t border-base-300">
              <p className="text-sm font-semibold truncate mb-2">{user?.email || 'Usuario'}</p>
              <button
                onClick={() => { signOut(); setMobileOpen(false); }}
                className="btn btn-ghost btn-sm w-full justify-start gap-2 text-error"
              >
                <LogOut size={16} /> Cerrar Sesión
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-base-100 shadow-sm p-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-primary">Pablito POS</h1>
          <button className="btn btn-square btn-ghost" onClick={() => setMobileOpen(true)}>
            <Menu size={22} />
          </button>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-base-200 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
