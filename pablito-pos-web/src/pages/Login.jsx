import { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Lock, Mail, Eye, EyeOff, AlertCircle, ShoppingCart, Search } from 'lucide-react';

const Login = () => {
  const { user, signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Si ya tiene sesión, redirigir al POS
  if (user) return <Navigate to="/pos" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signIn(email, password);
    } catch (err) {
      if (err.message.includes('Invalid login')) {
        setError('Correo o contraseña incorrectos.');
      } else if (err.message.includes('Email not confirmed')) {
        setError('Confirma tu correo electrónico antes de iniciar sesión.');
      } else {
        setError('Error de conexión. Intenta de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #11111b 0%, #181825 40%, #11111b 100%)' }}>
      
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute w-[500px] h-[500px] rounded-full opacity-[0.07]"
          style={{
            background: 'radial-gradient(circle, #6366f1, transparent 70%)',
            top: '-10%', right: '-5%',
            animation: 'float 8s ease-in-out infinite'
          }} />
        <div className="absolute w-[400px] h-[400px] rounded-full opacity-[0.05]"
          style={{
            background: 'radial-gradient(circle, #22d3ee, transparent 70%)',
            bottom: '-10%', left: '-5%',
            animation: 'float 10s ease-in-out infinite reverse'
          }} />
        <div className="absolute w-[300px] h-[300px] rounded-full opacity-[0.04]"
          style={{
            background: 'radial-gradient(circle, #a78bfa, transparent 70%)',
            top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
            animation: 'float 12s ease-in-out infinite'
          }} />
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
            backgroundSize: '60px 60px'
          }} />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo area */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-5 relative"
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%)',
              boxShadow: '0 20px 60px rgba(99, 102, 241, 0.3), 0 0 0 1px rgba(99, 102, 241, 0.1)',
            }}>
            <ShoppingCart size={36} className="text-white drop-shadow-lg" />
            {/* Glow ring */}
            <div className="absolute inset-0 rounded-2xl" 
              style={{ 
                boxShadow: '0 0 30px rgba(99, 102, 241, 0.4)',
                animation: 'pulse-glow 3s ease-in-out infinite' 
              }} />
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-2"
            style={{ 
              background: 'linear-gradient(135deg, #e2e8f0 0%, #f8fafc 50%, #cbd5e1 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
              letterSpacing: '-0.02em'
            }}>
            Pablito POS
          </h1>
          <p className="text-sm tracking-widest uppercase font-medium"
            style={{ color: '#64748b', letterSpacing: '0.2em' }}>
            Sistema de Punto de Venta
          </p>
        </div>

        {/* Login card */}
        <div className="rounded-2xl border overflow-hidden"
          style={{ 
            background: 'linear-gradient(180deg, rgba(30, 30, 46, 0.8) 0%, rgba(24, 24, 37, 0.9) 100%)',
            borderColor: 'rgba(148, 163, 184, 0.1)',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05)'
          }}>
          
          {/* Accent line at top */}
          <div className="h-[2px]" style={{ background: 'linear-gradient(90deg, transparent, #6366f1, #8b5cf6, #6366f1, transparent)' }} />
          
          <div className="p-8 sm:p-10">
            <h2 className="text-xl font-semibold text-center mb-1" style={{ color: '#f1f5f9' }}>
              Iniciar Sesión
            </h2>
            <p className="text-center mb-8" style={{ color: '#64748b', fontSize: '0.85rem' }}>
              Ingresa tus credenciales para acceder al sistema
            </p>

            {error && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl mb-6"
                style={{ 
                  background: 'rgba(239, 68, 68, 0.1)', 
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  color: '#fca5a5'
                }}>
                <AlertCircle size={18} style={{ color: '#f87171', flexShrink: 0 }} />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: '#94a3b8' }}>
                  Correo Electrónico
                </label>
                <div className="relative group">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors" size={18}
                    style={{ color: '#475569' }} />
                  <input
                    type="email"
                    required
                    placeholder="tu@correo.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    className="w-full h-12 pl-12 pr-4 rounded-xl text-sm outline-none transition-all duration-200"
                    style={{
                      background: 'rgba(17, 17, 27, 0.6)',
                      border: '1px solid rgba(148, 163, 184, 0.15)',
                      color: '#e2e8f0',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                      e.target.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.1)';
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = 'rgba(148, 163, 184, 0.15)';
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: '#94a3b8' }}>
                  Contraseña
                </label>
                <div className="relative group">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors" size={18}
                    style={{ color: '#475569' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    className="w-full h-12 pl-12 pr-12 rounded-xl text-sm outline-none transition-all duration-200"
                    style={{
                      background: 'rgba(17, 17, 27, 0.6)',
                      border: '1px solid rgba(148, 163, 184, 0.15)',
                      color: '#e2e8f0',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                      e.target.style.boxShadow = '0 0 0 3px rgba(99, 102, 241, 0.1)';
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = 'rgba(148, 163, 184, 0.15)';
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors hover:opacity-80"
                    style={{ color: '#475569' }}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Submit button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-12 rounded-xl font-semibold text-sm text-white transition-all duration-300 relative overflow-hidden group"
                style={{
                  background: loading 
                    ? 'rgba(99, 102, 241, 0.4)' 
                    : 'linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)',
                  boxShadow: loading ? 'none' : '0 8px 30px rgba(99, 102, 241, 0.3)',
                }}
                onMouseEnter={(e) => { if (!loading) e.target.style.boxShadow = '0 12px 40px rgba(99, 102, 241, 0.45)'; }}
                onMouseLeave={(e) => { if (!loading) e.target.style.boxShadow = '0 8px 30px rgba(99, 102, 241, 0.3)'; }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Verificando...
                  </span>
                ) : (
                  <span className="relative z-10">Ingresar al Sistema</span>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 space-y-4">
          <Link to="/verificacion" 
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium transition-all duration-300 hover:scale-105"
            style={{ 
              background: 'rgba(99, 102, 241, 0.1)', 
              border: '1px solid rgba(99, 102, 241, 0.3)',
              color: '#818cf8',
              boxShadow: '0 4px 15px rgba(0,0,0,0.2)'
            }}>
            <Search size={16} /> Consulta de Boletas y Facturas
          </Link>
          
          <div className="pt-2 space-y-2">
            <p className="text-xs" style={{ color: '#475569' }}>
              © {new Date().getFullYear()} Pablito POS — Acceso exclusivo para personal autorizado
            </p>
            <p className="text-xs" style={{ color: '#334155' }}>
              v2.0 · Facturación Electrónica SUNAT
            </p>
          </div>
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-30px); }
        }
        @keyframes pulse-glow {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.8; }
        }
        input::placeholder {
          color: #475569 !important;
        }
      `}</style>
    </div>
  );
};

export default Login;
