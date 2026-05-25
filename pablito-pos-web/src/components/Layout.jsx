import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { ShoppingCart, Package, Users, FileText, Settings, LayoutDashboard, LogOut, X, Menu, CreditCard } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const Layout = () => {
  const location = useLocation();
  const { user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigation = [
    { name: 'Ventas', href: '/pos', icon: ShoppingCart },
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Historial', href: '/historial', icon: FileText },
    { name: 'Clientes', href: '/clientes', icon: Users },
    { name: 'Productos', href: '/productos', icon: Package },
    { name: 'Fiados', href: '/fiados', icon: CreditCard },
    { name: 'Configuración', href: '/configuracion', icon: Settings },
  ];

  const NavLinks = ({ onNavigate }) => (
    <div className="flex flex-col gap-1">
      {navigation.map((item) => {
        const isActive = location.pathname === item.href;
        return (
          <Link
            key={item.name}
            to={item.href}
            onClick={onNavigate}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
              isActive 
                ? 'bg-primary/10 text-primary font-medium' 
                : 'text-base-content/50 hover:text-base-content/80 hover:bg-base-300/30'
            }`}
          >
            <item.icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
            <span className="tracking-[-0.01em]">{item.name}</span>
            {isActive && (
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />
            )}
          </Link>
        );
      })}
    </div>
  );

  return (
    <div className="flex h-screen bg-base-100">
      {/* Desktop Sidebar */}
      <div className="w-60 hidden md:flex md:flex-col border-r border-base-300/50">
        {/* Logo */}
        <div className="px-5 pt-6 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)' }}>
              <ShoppingCart size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-base-content">Pablito POS</h1>
              <p className="text-[10px] text-base-content/30 font-medium tracking-wider uppercase">Sistema de Ventas</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 overflow-y-auto">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-base-content/20 px-3 mb-2">Menú</p>
          <NavLinks />
        </nav>

        {/* User footer */}
        <div className="p-4 border-t border-base-300/50">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
              style={{ background: 'rgba(129, 140, 248, 0.1)', color: '#818cf8' }}>
              {user?.email?.substring(0, 2).toUpperCase() || 'US'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate text-base-content/70">{user?.email || 'Usuario'}</p>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                <p className="text-[10px] text-base-content/30">En línea</p>
              </div>
            </div>
          </div>
          <button
            onClick={signOut}
            className="btn btn-ghost btn-sm w-full justify-start gap-2 text-base-content/30 hover:text-error text-xs h-8"
          >
            <LogOut size={14} /> Cerrar Sesión
          </button>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-base-200 flex flex-col animate-slide-in shadow-2xl">
            <div className="p-5 flex justify-between items-center">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)' }}>
                  <ShoppingCart size={16} className="text-white" />
                </div>
                <h1 className="text-sm font-bold text-base-content">Pablito POS</h1>
              </div>
              <button className="btn btn-sm btn-circle btn-ghost text-base-content/30" onClick={() => setMobileOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <nav className="flex-1 px-3 overflow-y-auto">
              <NavLinks onNavigate={() => setMobileOpen(false)} />
            </nav>
            <div className="p-4 border-t border-base-300/50">
              <p className="text-xs text-base-content/40 truncate mb-2">{user?.email || 'Usuario'}</p>
              <button
                onClick={() => { signOut(); setMobileOpen(false); }}
                className="btn btn-ghost btn-sm w-full justify-start gap-2 text-base-content/30 hover:text-error text-xs"
              >
                <LogOut size={14} /> Cerrar Sesión
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-base-200/80 backdrop-blur-lg border-b border-base-300/50 px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)' }}>
              <ShoppingCart size={14} className="text-white" />
            </div>
            <h1 className="text-sm font-bold text-base-content">Pablito POS</h1>
          </div>
          <button className="btn btn-ghost btn-sm btn-square text-base-content/50" onClick={() => setMobileOpen(true)}>
            <Menu size={20} />
          </button>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-base-100 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
