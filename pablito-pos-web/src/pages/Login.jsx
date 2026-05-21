import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Lock, Mail, Eye, EyeOff, AlertCircle } from 'lucide-react';

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      {/* Fondo decorativo */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-secondary/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo y título */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary/20 backdrop-blur-sm border border-primary/30 mb-4 shadow-lg shadow-primary/20">
            <Lock size={36} className="text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Pablito POS
          </h1>
          <p className="text-slate-400 mt-2">Sistema de Punto de Venta</p>
        </div>

        {/* Card de login */}
        <div className="card bg-base-100/95 backdrop-blur-md shadow-2xl border border-base-300/50">
          <div className="card-body p-8">
            <h2 className="text-xl font-semibold text-center mb-1">Iniciar Sesión</h2>
            <p className="text-base-content/50 text-sm text-center mb-6">
              Ingresa tus credenciales para acceder al sistema
            </p>

            {error && (
              <div className="alert alert-error text-sm mb-4 py-3">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Correo Electrónico</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" size={20} />
                  <input
                    type="email"
                    required
                    placeholder="tu@correo.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input input-bordered w-full pl-11"
                    autoComplete="email"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Contraseña</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" size={20} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input input-bordered w-full pl-11 pr-11"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              {/* Botón de login */}
              <button
                type="submit"
                className="btn btn-primary w-full text-base"
                disabled={loading}
              >
                {loading ? (
                  <span className="loading loading-spinner loading-sm"></span>
                ) : (
                  'Ingresar al Sistema'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-slate-500 text-xs mt-6">
          © {new Date().getFullYear()} Pablito POS — Acceso exclusivo para personal autorizado.
        </p>
      </div>
    </div>
  );
};

export default Login;
