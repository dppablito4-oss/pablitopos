import React, { useState, useEffect } from 'react';
import { Save, Building2, Settings, AlertCircle, Users, Link, Trash2, Key, UserPlus, Check, Copy } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { logAudit } from '../services/auditService';
import { useCompany, TAX_REGIMES, REGIME_CONFIG } from '../contexts/CompanyContext';

const Configuracion = () => {
  const { refetchCompany } = useCompany();
  const [activeTab, setActiveTab] = useState('empresa'); // 'empresa' | 'personal'
  const [config, setConfig] = useState({
    name: '', ruc: '', address: '', phone: '', email: '', website: '',
    footer_message: '', include_igv: true, brand_color: '#4f46e5',
    sol_user: 'MODDATOS', sol_pass: 'MODDATOS', cert_pem: '', production: false,
    tax_regime: 'nrus', logo_base64: ''
  });
  const [isLoading, setIsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [companyId, setCompanyId] = useState(null);

  // Estados para la Gestión de Personal
  const [cajeros, setCajeros] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [cajeroEmail, setCajeroEmail] = useState('');
  const [generatingInvite, setGeneratingInvite] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  useEffect(() => {
    if (companyId && activeTab === 'personal') {
      fetchPersonalData();
    }
  }, [companyId, activeTab]);

  const fetchConfig = async () => {
    setIsLoading(true);
    // Cargar perfil de la empresa vinculada al usuario activo
    const { data: profileData } = await supabase.auth.getUser();
    if (!profileData?.user) {
      setIsLoading(false);
      return;
    }

    const { data: userProfile } = await supabase
      .from('profiles')
      .select('company_id')
      .eq('id', profileData.user.id)
      .single();

    if (userProfile?.company_id) {
      setCompanyId(userProfile.company_id);
      
      const { data, error } = await supabase
        .from('company_profile')
        .select('*')
        .eq('id', userProfile.company_id)
        .single();

      if (data) {
        setConfig({
          name: data.name || '',
          ruc: data.ruc || '',
          address: data.address || '',
          phone: data.phone || '',
          email: data.email || '',
          website: data.website || '',
          footer_message: data.footer_message || '',
          include_igv: data.include_igv ?? true,
          brand_color: data.brand_color || '#4f46e5',
          sol_user: data.sol_user || 'MODDATOS',
          sol_pass: data.sol_pass || 'MODDATOS',
          cert_pem: data.cert_pem || '',
          production: data.production ?? false,
          tax_regime: data.tax_regime || 'nrus',
          logo_base64: data.logo_base64 || ''
        });
      }
      if (error && error.code !== 'PGRST116') setError(error.message);
    }
    setIsLoading(false);
  };

  const fetchPersonalData = async () => {
    if (!companyId) return;

    // 1. Cargar cajeros vinculados a la tienda
    const { data: cajerosData, error: errCajeros } = await supabase
      .from('profiles')
      .select('*')
      .eq('company_id', companyId)
      .eq('role', 'cajero');

    if (cajerosData) setCajeros(cajerosData);

    // 2. Cargar invitaciones de tipo 'cajero' activas
    const { data: invitesData } = await supabase
      .from('invitations')
      .select('*')
      .eq('company_id', companyId)
      .eq('type', 'cajero')
      .order('created_at', { ascending: false });

    if (invitesData) setInvitations(invitesData);
  };

  const handleSave = async () => {
    if (!config.name.trim()) return alert('El nombre o razón social es obligatorio.');
    setSaving(true);
    setSaved(false);
    setError(null);
    const payload = { ...config, updated_at: new Date().toISOString() };
    let err;
    if (companyId) {
      const { error } = await supabase.from('company_profile').update(payload).eq('id', companyId);
      err = error;
    } else {
      const { data, error } = await supabase.from('company_profile').insert([{ ...payload, is_active: true }]).select().single();
      if (data) setCompanyId(data.id);
      err = error;
    }
    setSaving(false);
    if (err) { setError(err.message); return; }
    setSaved(true);
    logAudit('CONFIG_GUARDADA', config.name);
    if (typeof refetchCompany === 'function') refetchCompany();
    setTimeout(() => setSaved(false), 3000);
  };

  const handleLogoUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const MAX_WIDTH = 300;
        const scaleSize = Math.min(MAX_WIDTH / img.width, 1);
        canvas.width = img.width * scaleSize;
        canvas.height = img.height * scaleSize;

        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        const dataUrl = canvas.toDataURL('image/png', 0.8);
        setConfig({ ...config, logo_base64: dataUrl });
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  };

  // Crear Invitación para Cajero
  const handleGenerateCajeroInvite = async (e) => {
    e.preventDefault();
    if (!companyId) return;
    setGeneratingInvite(true);

    try {
      const newInvite = {
        type: 'cajero',
        company_id: companyId,
        email: cajeroEmail || null,
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24h
        is_used: false
      };

      const { data, error } = await supabase
        .from('invitations')
        .insert([newInvite])
        .select()
        .single();

      if (error) throw error;

      setCajeroEmail('');
      fetchPersonalData();
    } catch (err) {
      console.error(err);
      alert(err.message || 'No se pudo generar la invitación.');
    } finally {
      setGeneratingInvite(false);
    }
  };

  // Eliminar Invitación
  const handleDeleteInvite = async (id) => {
    if (!confirm('¿Estás seguro de cancelar este enlace de invitación?')) return;
    const { error } = await supabase.from('invitations').delete().eq('id', id);
    if (!error) fetchPersonalData();
  };

  // Desvincular Cajero (Quitar acceso a la tienda)
  const handleRemoveCajero = async (id) => {
    if (!confirm('¿Estás seguro de remover el acceso a este cajero? Ya no podrá ingresar a la tienda.')) return;
    const { error } = await supabase
      .from('profiles')
      .update({ company_id: null })
      .eq('id', id);

    if (!error) {
      logAudit('PERSONAL_REMOVIDO', id);
      fetchPersonalData();
    }
  };

  const copyToClipboard = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (isLoading) return (
    <div className="flex items-center justify-center h-full">
      <span className="loading loading-spinner loading-lg text-primary"></span>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto w-full pb-10 text-base-content">
      
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Configuración del Sistema</h2>
          <p className="text-base-content/60 text-sm">Administra los datos de tu empresa, preferencias y accesos del personal.</p>
        </div>
        {activeTab === 'empresa' && (
          <button className="btn btn-primary btn-sm rounded-xl h-10" onClick={handleSave} disabled={saving}>
            {saving
              ? <span className="loading loading-spinner loading-sm"/>
              : <><Save size={16}/> Guardar Cambios</>}
          </button>
        )}
      </div>

      {/* Selector de Pestañas Premium */}
      <div className="flex border-b border-base-300 gap-1 pb-1">
        <button 
          onClick={() => setActiveTab('empresa')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${activeTab === 'empresa' ? 'bg-primary text-white shadow-sm' : 'text-base-content/60 hover:bg-base-200'}`}
        >
          <Building2 size={16} />
          Datos y Preferencias
        </button>
        <button 
          onClick={() => setActiveTab('personal')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${activeTab === 'personal' ? 'bg-primary text-white shadow-sm' : 'text-base-content/60 hover:bg-base-200'}`}
        >
          <Users size={16} />
          Gestión de Personal (Cajeros)
        </button>
      </div>

      {saved && (
        <div className="alert alert-success shadow-sm rounded-xl">
          <span>Local guardado correctamente.</span>
        </div>
      )}
      {error && (
        <div className="alert alert-error shadow-sm rounded-xl">
          <AlertCircle size={18}/> <span>Error: {error}</span>
        </div>
      )}

      {/* PESTAÑA: DATOS Y PREFERENCIAS */}
      {activeTab === 'empresa' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Datos de Empresa */}
          <div className="glass-card">
            <div className="card-body">
              <h3 className="card-title text-lg flex gap-2">
                <Building2 size={20}/> Datos de la Empresa
              </h3>
              <div className="divider mt-0 mb-2"/>

              <div className="form-control w-full">
                <label className="label"><span className="label-text font-semibold">Nombre / Razón Social *</span></label>
                <input type="text" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="Ej. Bodega La Esquina"
                  value={config.name} onChange={e => setConfig({...config, name: e.target.value})} />
              </div>

              <div className="form-control w-full">
                <label className="label"><span className="label-text">RUC / DNI</span></label>
                <input type="text" maxLength={11} className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="Ej. 20123456789"
                  value={config.ruc} onChange={e => setConfig({...config, ruc: e.target.value.replace(/\D/g,'')})} />
              </div>

              <div className="form-control w-full">
                <label className="label"><span className="label-text">Dirección</span></label>
                <input type="text" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="Dirección del local"
                  value={config.address} onChange={e => setConfig({...config, address: e.target.value})} />
              </div>

              {/* LOGO UPLOAD */}
              <div className="form-control w-full">
                <label className="label"><span className="label-text font-semibold">Logo de la Empresa</span></label>
                <div className="flex items-center gap-4">
                  {config.logo_base64 && <img src={config.logo_base64} alt="Logo" className="w-16 h-16 object-contain bg-white rounded-xl border p-1" />}
                  <input type="file" accept="image/png, image/jpeg" className="file-input file-input-bordered file-input-sm w-full rounded-xl text-xs" onChange={handleLogoUpload} />
                  {config.logo_base64 && <button className="btn btn-sm btn-ghost text-error" onClick={() => setConfig({...config, logo_base64: ''})}>X</button>}
                </div>
                <label className="label"><span className="label-text-alt text-base-content/50">Se convertirá automáticamente para tickets térmicos (max 300px).</span></label>
              </div>

              {/* RÉGIMEN TRIBUTARIO */}
              <div className="form-control w-full">
                <label className="label"><span className="label-text font-semibold">Régimen Tributario</span></label>
                <select className="select select-bordered w-full rounded-xl text-xs h-10" value={config.tax_regime}
                  onChange={e => setConfig({...config, tax_regime: e.target.value})}>
                  {Object.entries(TAX_REGIMES).map(([key, val]) => (
                    <option key={val} value={val}>{REGIME_CONFIG[val].name}</option>
                  ))}
                </select>
                <label className="label">
                  <span className="label-text-alt">
                    {REGIME_CONFIG[config.tax_regime]?.hasIgv ? '✅ IGV activo (18%)' : '❌ Sin IGV'}
                    {' · '}
                    {REGIME_CONFIG[config.tax_regime]?.canEmitFactura ? '✅ Facturas habilitadas' : '❌ Solo boletas'}
                    {REGIME_CONFIG[config.tax_regime]?.monthlyLimit ? ` · Límite: S/${REGIME_CONFIG[config.tax_regime].monthlyLimit}` : ' · Sin límite mensual'}
                  </span>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="form-control w-full">
                  <label className="label"><span className="label-text">Teléfono</span></label>
                  <input type="text" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="9XXXXXXXX"
                    value={config.phone} onChange={e => setConfig({...config, phone: e.target.value})} />
                </div>
                <div className="form-control w-full">
                  <label className="label"><span className="label-text">Email</span></label>
                  <input type="email" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="correo@empresa.com"
                    value={config.email} onChange={e => setConfig({...config, email: e.target.value})} />
                </div>
              </div>

              <div className="form-control w-full">
                <label className="label"><span className="label-text">Sitio Web</span></label>
                <input type="text" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="www.miempresa.com"
                  value={config.website} onChange={e => setConfig({...config, website: e.target.value})} />
              </div>
            </div>
          </div>

          {/* Preferencias */}
          <div className="glass-card">
            <div className="card-body">
              <h3 className="card-title text-lg flex gap-2">
                <Settings size={20}/> Preferencias de Venta
              </h3>
              <div className="divider mt-0 mb-2"/>

              <div className="form-control w-full">
                <label className="label cursor-pointer">
                  <div>
                    <span className="label-text font-semibold">Incluir IGV (18%) en precios</span>
                    <p className="text-xs text-base-content/50">Si está activo, el total incluye el 18% de impuesto.</p>
                  </div>
                  <input type="checkbox" className="toggle toggle-primary" checked={config.include_igv}
                    onChange={e => setConfig({...config, include_igv: e.target.checked})} />
                </label>
              </div>

              <div className="divider my-1"/>

              <div className="form-control w-full">
                <label className="label"><span className="label-text font-semibold">Color de marca</span></label>
                <div className="flex items-center gap-3">
                  <input type="color" className="w-12 h-10 rounded cursor-pointer border border-base-300"
                    value={config.brand_color} onChange={e => setConfig({...config, brand_color: e.target.value})} />
                  <span className="font-mono text-sm text-base-content/70">{config.brand_color}</span>
                </div>
              </div>

              <div className="divider my-1"/>

              <div className="form-control w-full">
                <label className="label"><span className="label-text font-semibold">Mensaje al pie del ticket</span></label>
                <textarea className="textarea textarea-bordered w-full rounded-xl text-xs h-28"
                  placeholder="Ej: ¡Gracias por su preferencia! Vuelva pronto."
                  value={config.footer_message}
                  onChange={e => setConfig({...config, footer_message: e.target.value})} />
              </div>
            </div>
          </div>

          {/* Credenciales de Facturación SUNAT */}
          <div className="glass-card col-span-1 md:col-span-2">
            <div className="card-body">
              <h3 className="card-title text-lg flex gap-2">
                <Building2 size={20}/> Facturación Electrónica (SUNAT)
              </h3>
              <p className="text-xs text-base-content/50">Configura tus credenciales SOL y carga tu certificado digital para firmar los XMLs.</p>
              <div className="divider mt-0 mb-2"/>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="form-control w-full">
                  <label className="label"><span className="label-text font-semibold">Usuario SOL</span></label>
                  <input type="text" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="Ej: MODDATOS"
                    value={config.sol_user} onChange={e => setConfig({...config, sol_user: e.target.value})} />
                </div>
                
                <div className="form-control w-full">
                  <label className="label"><span className="label-text font-semibold">Clave SOL</span></label>
                  <input type="password" className="input input-bordered w-full rounded-xl text-xs h-10" placeholder="Ej: MODDATOS"
                    value={config.sol_pass} onChange={e => setConfig({...config, sol_pass: e.target.value})} />
                </div>

                <div className="form-control w-full">
                  <label className="label cursor-pointer h-full flex items-end pb-3">
                    <div className="flex flex-col">
                      <span className="label-text font-semibold">Modo Producción</span>
                      <span className="text-xs text-base-content/50">Activar para comprobantes reales</span>
                    </div>
                    <input type="checkbox" className="toggle toggle-secondary" checked={config.production}
                      onChange={e => setConfig({...config, production: e.target.checked})} />
                  </label>
                </div>
              </div>

              <div className="form-control w-full mt-4">
                <label className="label">
                  <span className="label-text font-semibold">Certificado Digital (PEM)</span>
                  <span className="text-xs text-primary cursor-pointer hover:underline">
                    <input type="file" accept=".pem" className="hidden" id="cert-upload" onChange={(e) => {
                      const file = e.target.files[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onload = (evt) => {
                          setConfig({...config, cert_pem: evt.target.result});
                        };
                        reader.readAsText(file);
                      }
                    }} />
                    <label htmlFor="cert-upload" className="cursor-pointer">📁 Cargar archivo .pem</label>
                  </span>
                </label>
                <textarea className="textarea textarea-bordered w-full font-mono text-xs h-32 rounded-xl"
                  placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                  value={config.cert_pem}
                  onChange={e => setConfig({...config, cert_pem: e.target.value})} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PESTAÑA: GESTIÓN DE PERSONAL */}
      {activeTab === 'personal' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Creador de Enlaces */}
          <div className="glass-card lg:col-span-1 h-fit">
            <div className="card-body">
              <h3 className="card-title text-base font-bold flex gap-2">
                <UserPlus size={18}/> Crear Acceso a Cajero
              </h3>
              <p className="text-[11px] text-base-content/50 mt-1">
                Genera un link único auto-destructible para que tu personal cree su cuenta vinculada a esta tienda.
              </p>
              <div className="divider mt-2 mb-3"/>

              <form onSubmit={handleGenerateCajeroInvite} className="space-y-4">
                <div className="form-control w-full">
                  <label className="label text-[10px] font-bold uppercase pb-1">
                    Correo del Cajero (Opcional)
                  </label>
                  <input 
                    type="email" 
                    placeholder="cajero@correo.com"
                    value={cajeroEmail}
                    onChange={(e) => setCajeroEmail(e.target.value)}
                    className="input input-bordered w-full rounded-xl text-xs h-9"
                  />
                </div>

                <button 
                  type="submit" 
                  disabled={generatingInvite || !companyId}
                  className="btn btn-primary btn-sm w-full rounded-xl text-xs h-9 font-bold"
                >
                  {generatingInvite ? (
                    <span className="loading loading-spinner loading-xs"></span>
                  ) : (
                    'Generar Link de Registro'
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Listado de Enlaces Activos & Personal */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Lista de Invitaciones Activas */}
            <div className="glass-card">
              <div className="card-body">
                <h3 className="card-title text-sm font-bold flex gap-2">
                  <Link size={16}/> Enlaces de Invitación Activos
                </h3>
                <div className="divider mt-1 mb-2"/>

                {invitations.filter(i => !i.is_used).length === 0 ? (
                  <p className="text-xs text-base-content/40 text-center py-4">No hay enlaces de invitación pendientes.</p>
                ) : (
                  <div className="overflow-x-auto text-xs">
                    <table className="table table-compact w-full">
                      <thead>
                        <tr className="bg-base-300/40">
                          <th>Destinatario</th>
                          <th>Link Temporal</th>
                          <th className="text-right">Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {invitations.filter(i => !i.is_used).map((inv) => {
                          // BUG-036 FIX: Incluir el hash en la URL para HashRouter
                          const registerLink = `${window.location.origin}${window.location.pathname}#/registrarse?invite=${inv.id}`;
                          const isExpired = new Date(inv.expires_at) < new Date();
                          return (
                            <tr key={inv.id} className="hover:bg-base-300/10">
                              <td className="font-semibold text-base-content/85">
                                {inv.email || <span className="italic text-base-content/40">Cualquiera</span>}
                                {isExpired && <span className="badge badge-error badge-xs ml-2">Expirado</span>} {/* BUG-015 FIX */}
                              </td>
                              <td>
                                <div className="flex items-center gap-2 max-w-[200px] sm:max-w-none">
                                  <input 
                                    type="text" 
                                    readOnly 
                                    value={registerLink} 
                                    className="input input-xs bg-base-300 w-full rounded-lg text-[10px] h-6 cursor-default focus:outline-none"
                                  />
                                  <button 
                                    onClick={() => copyToClipboard(inv.id, registerLink)}
                                    className={`btn btn-xs rounded-lg h-6 min-h-0 ${copiedId === inv.id ? 'btn-success' : 'btn-ghost border border-base-300'}`}
                                  >
                                    {copiedId === inv.id ? <Check size={10} /> : <Copy size={10} />}
                                  </button>
                                </div>
                              </td>
                              <td className="text-right">
                                <button 
                                  onClick={() => handleDeleteInvite(inv.id)} 
                                  className="btn btn-ghost btn-xs text-error"
                                >
                                  <Trash2 size={12} />
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Listado de Cajeros Activos */}
            <div className="glass-card">
              <div className="card-body">
                <h3 className="card-title text-sm font-bold flex gap-2">
                  <Users size={16}/> Vendedores / Cajeros Habilitados
                </h3>
                <div className="divider mt-1 mb-2"/>

                {cajeros.length === 0 ? (
                  <p className="text-xs text-base-content/40 text-center py-4">No tienes cajeros registrados todavía.</p>
                ) : (
                  <div className="overflow-x-auto text-xs">
                    <table className="table table-compact w-full">
                      <thead>
                        <tr className="bg-base-300/40">
                          <th>Nombre</th>
                          <th>Correo</th>
                          <th className="text-right">Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cajeros.map((user) => (
                          <tr key={user.id} className="hover:bg-base-300/10">
                            <td className="font-semibold text-base-content/85">{user.full_name}</td>
                            <td>{user.email || <span className="italic text-base-content/40">Sin correo</span>}</td>
                            <td className="text-right">
                              <button 
                                onClick={() => handleRemoveCajero(user.id)}
                                className="btn btn-ghost btn-xs text-error font-bold"
                              >
                                Revocar Acceso
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

          </div>

        </div>
      )}

      {/* Info sobre tablas requeridas */}
      {!companyId && !isLoading && (
        <div className="alert alert-info shadow-sm text-sm rounded-xl">
          <AlertCircle size={18}/>
          <span>No se encontró un perfil de empresa. Completa los datos y guarda para crear uno nuevo.</span>
        </div>
      )}
    </div>
  );
};

export default Configuracion;
