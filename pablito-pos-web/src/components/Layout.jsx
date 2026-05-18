import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShoppingCart, Users, Package, Settings, History } from 'lucide-react';

const Layout = () => {
  const location = useLocation();

  const navigation = [
    { name: 'POS (Ventas)', href: '/pos', icon: ShoppingCart },
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Historial', href: '/historial', icon: History },
    { name: 'Clientes', href: '/clientes', icon: Users },
    { name: 'Productos', href: '/productos', icon: Package },
    { name: 'Configuración', href: '/configuracion', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-base-200">
      {/* Sidebar */}
      <div className="w-64 bg-base-100 shadow-xl hidden md:flex md:flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary">Pablito POS</h1>
          <p className="text-sm text-base-content/60">Sistema de Ventas</p>
        </div>
        <nav className="flex-1 px-4 space-y-2 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
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
        </nav>
        <div className="p-4 border-t border-base-300">
          <div className="flex items-center gap-3">
            <div className="avatar placeholder">
              <div className="bg-neutral text-neutral-content rounded-full w-10">
                <span className="text-xs">ADM</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold">Cajero Activo</p>
              <p className="text-xs text-success">En línea</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-base-100 shadow-sm p-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-primary">Pablito POS</h1>
          <button className="btn btn-square btn-ghost">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-5 h-5 stroke-current"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
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
