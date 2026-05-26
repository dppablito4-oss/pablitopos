import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../hooks/useAuth';
import { Shield, Plus, Copy, Check, Users, Building2, Ticket, Mail, RefreshCw, Trash2, Clock } from 'lucide-react';

const SuperAdmin = () => {
  const { profile } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [email, setEmail] = useState('');
  const [generating, setGenerating] = useState(false);
  const [copiedId, setCopiedId] = useState('');

  // Cargar datos principales
  const loadData = async () => {
    setRefreshing(true);
    try {
      // 1. Cargar todas las empresas
      const { data: cos, error: errCos } = await supabase
        .from('company_profile')
        .select('*')
        .order('id', { ascending: true });
      if (!errCos) setCompanies(cos || []);

      // 2. Cargar todas las invitaciones
      const { data: invs, error: errInvs } = await supabase
        .from('invitations')
        .select('*')
        .order('created_at', { ascending: false });
      if (!errInvs) setInvitations(invs || []);

    } catch (e) {
      console.error('Error loading admin data:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (profile?.role === 'superadmin') {
      loadData();
    }
  }, [profile]);

  // Generar un link de invitación
  const handleCreateInvitation = async (e) => {
    e.preventDefault();
    setGenerating(true);
    try {
      const { data, error } = await supabase
        .from('invitations')
        .insert([{ email: email || null }])
        .select()
        .single();

      if (error) throw error;

      setEmail('');
      loadData();
    } catch (err) {
      console.error('Error creating invitation:', err);
      alert('Error al crear invitación: ' + err.message);
    } finally {
      setGenerating(false);
    }
  };

  // Copiar link de invitación
  const copyInviteLink = (id) => {
    const baseUrl = window.location.origin + window.location.pathname; // http://domain/#/
    const link = `${baseUrl}#/registrarse?invite=${id}`;
    navigator.clipboard.writeText(link);
    setCopiedId(id);
    setTimeout(() => setCopiedId(''), 2000);
  };

  // Eliminar/Cancelar invitación
  const handleDeleteInvitation = async (id) => {
    if (!confirm('¿Estás seguro de cancelar esta invitación?')) return;
    try {
      const { error } = await supabase
        .from('invitations')
        .delete()
        .eq('id', id);
      if (error) throw error;
      loadData();
    } catch (err) {
      console.error('Error deleting invitation:', err);
    }
  };

  if (profile?.role !== 'superadmin') {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="text-center p-8 bg-error/10 border border-error/20 rounded-2xl max-w-md">
          <Shield size={48} className="mx-auto text-error mb-4" />
          <h2 className="text-xl font-bold text-base-content mb-2">Acceso Denegado</h2>
          <p className="text-sm text-base-content/60">
            No tienes los permisos de Super Administrador necesarios para acceder a este panel.
          </p>
        </div>
      </div>
    );
  }

  const activeCompanies = companies.filter(c => c.is_active).length;
  const pendingInvitations = invitations.filter(i => !i.is_used && new Date(i.expires_at) > new Date()).length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Shield className="text-primary" size={24} />
            SaaS Panel de Control
          </h1>
          <p className="text-xs text-base-content/50">Administra tus clientes, licencias e invitaciones de un solo uso.</p>
        </div>
        <button 
          onClick={loadData} 
          disabled={refreshing}
          className="btn btn-sm btn-ghost gap-2 text-xs"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Actualizar Datos
        </button>
      </div>

      {/* METRICS */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-base-200/50 border border-base-300 p-5 rounded-2xl flex items-center gap-4">
          <div className="p-3.5 bg-primary/10 rounded-xl text-primary">
            <Building2 size={24} />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-base-content/40">Total Empresas</p>
            <p className="text-2xl font-bold mt-0.5">{companies.length}</p>
          </div>
        </div>

        <div className="bg-base-200/50 border border-base-300 p-5 rounded-2xl flex items-center gap-4">
          <div className="p-3.5 bg-success/10 rounded-xl text-success">
            <Check size={24} />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-base-content/40">Empresas Activas</p>
            <p className="text-2xl font-bold mt-0.5">{activeCompanies}</p>
          </div>
        </div>

        <div className="bg-base-200/50 border border-base-300 p-5 rounded-2xl flex items-center gap-4">
          <div className="p-3.5 bg-warning/10 rounded-xl text-warning">
            <Clock size={24} />
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-base-content/40">Invitaciones Activas</p>
            <p className="text-2xl font-bold mt-0.5">{pendingInvitations}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: CREATE INVITATION */}
        <div className="bg-base-200/40 border border-base-300/60 p-5 rounded-2xl h-fit space-y-4">
          <h2 className="text-sm font-bold tracking-tight flex items-center gap-2">
            <Plus className="text-primary" size={16} />
            Crear Invitación Temporal
          </h2>
          <p className="text-xs text-base-content/50 leading-relaxed">
            Genera un enlace de registro auto-destructible de un solo uso. Expira en 24 horas después de creado.
          </p>

          <form onSubmit={handleCreateInvitation} className="space-y-3">
            <div>
              <label className="label text-[10px] font-semibold uppercase text-base-content/40 pb-1">
                Correo Electrónico (Opcional)
              </label>
              <div className="relative">
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="cliente@correo.com"
                  className="input input-sm input-bordered w-full pl-8 text-xs h-9 rounded-xl"
                />
                <Mail className="absolute left-2.5 top-2.5 text-base-content/30" size={14} />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={generating}
              className="btn btn-sm btn-primary w-full gap-2 text-xs h-9 rounded-xl font-bold"
            >
              {generating ? (
                <span className="loading loading-spinner loading-xs"></span>
              ) : (
                <Plus size={14} />
              )}
              Generar Link de Registro
            </button>
          </form>
        </div>

        {/* RIGHT COLUMN: INVITATIONS LIST & COMPANIES */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* INVITATIONS LIST */}
          <div className="bg-base-200/40 border border-base-300/60 p-5 rounded-2xl space-y-4">
            <h2 className="text-sm font-bold tracking-tight">Invitaciones de Registro</h2>
            
            {invitations.length === 0 ? (
              <p className="text-xs text-base-content/40 py-6 text-center">No hay invitaciones creadas todavía.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="table table-xs w-full text-xs">
                  <thead>
                    <tr className="border-b border-base-300/45 text-base-content/40">
                      <th>Correo</th>
                      <th>Estado</th>
                      <th>Expiración</th>
                      <th className="text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invitations.map((inv) => {
                      const isExpired = new Date(inv.expires_at) < new Date();
                      const status = inv.is_used 
                        ? { label: 'Usado', class: 'badge-success/20 text-success' } 
                        : isExpired 
                          ? { label: 'Expirado', class: 'badge-error/20 text-error' } 
                          : { label: 'Activo', class: 'badge-warning/20 text-warning animate-pulse' };

                      return (
                        <tr key={inv.id} className="border-b border-base-300/30">
                          <td className="font-mono text-[10px] text-base-content/75 py-2.5">
                            {inv.email || '(Invitación Pública)'}
                          </td>
                          <td>
                            <span className={`badge badge-xs font-semibold ${status.class}`}>
                              {status.label}
                            </span>
                          </td>
                          <td className="text-base-content/40 text-[10px]">
                            {new Date(inv.expires_at).toLocaleDateString()} {new Date(inv.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="text-right py-1">
                            <div className="flex justify-end gap-1.5">
                              {!inv.is_used && !isExpired && (
                                <button 
                                  onClick={() => copyInviteLink(inv.id)}
                                  className="btn btn-ghost btn-xs text-primary"
                                  title="Copiar link"
                                >
                                  {copiedId === inv.id ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                                </button>
                              )}
                              <button 
                                onClick={() => handleDeleteInvitation(inv.id)}
                                className="btn btn-ghost btn-xs text-error/60 hover:text-error"
                                title="Eliminar invitación"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* REGISTERED COMPANIES */}
          <div className="bg-base-200/40 border border-base-300/60 p-5 rounded-2xl space-y-4">
            <h2 className="text-sm font-bold tracking-tight">Empresas Registradas</h2>
            
            {companies.length === 0 ? (
              <p className="text-xs text-base-content/40 py-6 text-center">Cargando empresas...</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {companies.map((co) => (
                  <div key={co.id} className="bg-base-200/60 border border-base-300/40 p-4 rounded-xl flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5">
                        <p className="text-xs font-bold text-base-content">{co.name}</p>
                        <span className={`w-1.5 h-1.5 rounded-full ${co.is_active ? 'bg-success' : 'bg-base-content/30'}`} />
                      </div>
                      <p className="text-[10px] font-mono text-base-content/50">RUC: {co.ruc || 'No registrado'}</p>
                      <p className="text-[9px] text-base-content/40 truncate max-w-[200px]">{co.address || 'Sin dirección'}</p>
                    </div>
                    <span className="badge badge-outline badge-xs capitalize text-[9px]">
                      {co.tax_regime || 'NRUS'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default SuperAdmin;
