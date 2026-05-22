import React, { useState, useEffect } from 'react';
import { Save, Building2, Settings, AlertCircle } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { logAudit } from '../services/auditService';
import { useCompany, TAX_REGIMES, REGIME_CONFIG } from '../contexts/CompanyContext';

const Configuracion = () => {
  const { refetchCompany } = useCompany();
  const [config, setConfig] = useState({
    name: '', ruc: '', address: '', phone: '', email: '', website: '',
    footer_message: '', include_igv: true, brand_color: '#4f46e5',
    sol_user: 'MODDATOS', sol_pass: 'MODDATOS', cert_pem: '', production: false,
    tax_regime: 'nrus'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [companyId, setCompanyId] = useState(null);

  useEffect(() => { fetchConfig(); }, []);

  const fetchConfig = async () => {
    setIsLoading(true);
    const { data, error } = await supabase
      .from('company_profile')
      .select('*')
      .eq('is_active', true)
      .limit(1)
      .single();
    if (data) {
      setCompanyId(data.id);
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
        tax_regime: data.tax_regime || 'nrus'
      });
    }
    if (error && error.code !== 'PGRST116') setError(error.message);
    setIsLoading(false);
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
    // Refrescar contexto global de empresa
    if (typeof refetchCompany === 'function') refetchCompany();
    setTimeout(() => setSaved(false), 3000);
  };

  if (isLoading) return (
    <div className="flex items-center justify-center h-full">
      <span className="loading loading-spinner loading-lg text-primary"></span>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto w-full">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Configuración del Sistema</h2>
          <p className="text-base-content/60 text-sm">Datos de tu empresa y preferencias del POS</p>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving
            ? <span className="loading loading-spinner loading-sm"/>
            : <><Save size={20}/> Guardar Cambios</>}
        </button>
      </div>

      {saved && (
        <div className="alert alert-success shadow-sm">
          <span>✅ Configuración guardada correctamente.</span>
        </div>
      )}
      {error && (
        <div className="alert alert-error shadow-sm">
          <AlertCircle size={18}/> <span>Error: {error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Datos de Empresa */}
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg flex gap-2">
              <Building2 size={20}/> Datos de la Empresa
            </h3>
            <div className="divider mt-0 mb-2"/>

            <div className="form-control">
              <label className="label"><span className="label-text font-semibold">Nombre / Razón Social *</span></label>
              <input type="text" className="input input-bordered" placeholder="Ej. Bodega La Esquina"
                value={config.name} onChange={e => setConfig({...config, name: e.target.value})} />
            </div>

            <div className="form-control">
              <label className="label"><span className="label-text">RUC / DNI</span></label>
              <input type="text" maxLength={11} className="input input-bordered" placeholder="Ej. 20123456789"
                value={config.ruc} onChange={e => setConfig({...config, ruc: e.target.value.replace(/\D/g,'')})} />
            </div>

            <div className="form-control">
              <label className="label"><span className="label-text">Dirección</span></label>
              <input type="text" className="input input-bordered" placeholder="Dirección del local"
                value={config.address} onChange={e => setConfig({...config, address: e.target.value})} />
            </div>

            {/* RÉGIMEN TRIBUTARIO */}
            <div className="form-control">
              <label className="label"><span className="label-text font-semibold">Régimen Tributario</span></label>
              <select className="select select-bordered" value={config.tax_regime}
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
              <div className="form-control">
                <label className="label"><span className="label-text">Teléfono</span></label>
                <input type="text" className="input input-bordered" placeholder="9XXXXXXXX"
                  value={config.phone} onChange={e => setConfig({...config, phone: e.target.value})} />
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text">Email</span></label>
                <input type="email" className="input input-bordered" placeholder="correo@empresa.com"
                  value={config.email} onChange={e => setConfig({...config, email: e.target.value})} />
              </div>
            </div>

            <div className="form-control">
              <label className="label"><span className="label-text">Sitio Web</span></label>
              <input type="text" className="input input-bordered" placeholder="www.miempresa.com"
                value={config.website} onChange={e => setConfig({...config, website: e.target.value})} />
            </div>
          </div>
        </div>

        {/* Preferencias */}
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg flex gap-2">
              <Settings size={20}/> Preferencias de Venta
            </h3>
            <div className="divider mt-0 mb-2"/>

            <div className="form-control">
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

            <div className="form-control">
              <label className="label"><span className="label-text font-semibold">Color de marca</span></label>
              <div className="flex items-center gap-3">
                <input type="color" className="w-12 h-10 rounded cursor-pointer border border-base-300"
                  value={config.brand_color} onChange={e => setConfig({...config, brand_color: e.target.value})} />
                <span className="font-mono text-sm text-base-content/70">{config.brand_color}</span>
              </div>
            </div>

            <div className="divider my-1"/>

            <div className="form-control">
              <label className="label"><span className="label-text font-semibold">Mensaje al pie del ticket</span></label>
              <textarea className="textarea textarea-bordered h-28"
                placeholder="Ej: ¡Gracias por su preferencia! Vuelva pronto."
                value={config.footer_message}
                onChange={e => setConfig({...config, footer_message: e.target.value})} />
            </div>
          </div>
        </div>

        {/* Credenciales de Facturación SUNAT */}
        <div className="card bg-base-100 shadow-sm col-span-1 md:col-span-2">
          <div className="card-body">
            <h3 className="card-title text-lg flex gap-2">
              <Building2 size={20}/> Facturación Electrónica (SUNAT)
            </h3>
            <p className="text-xs text-base-content/50">Configura tus credenciales SOL y carga tu certificado digital para firmar los XMLs.</p>
            <div className="divider mt-0 mb-2"/>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="form-control">
                <label className="label"><span className="label-text font-semibold">Usuario SOL</span></label>
                <input type="text" className="input input-bordered" placeholder="Ej: MODDATOS"
                  value={config.sol_user} onChange={e => setConfig({...config, sol_user: e.target.value})} />
              </div>
              
              <div className="form-control">
                <label className="label"><span className="label-text font-semibold">Clave SOL</span></label>
                <input type="password" className="input input-bordered" placeholder="Ej: MODDATOS"
                  value={config.sol_pass} onChange={e => setConfig({...config, sol_pass: e.target.value})} />
              </div>

              <div className="form-control">
                <label className="label cursor-pointer h-full flex items-end pb-3">
                  <div className="flex flex-col">
                    <span className="label-text font-semibold">Modo Producción</span>
                    <span className="text-xs text-base-content/50">Activar para enviar comprobantes reales</span>
                  </div>
                  <input type="checkbox" className="toggle toggle-secondary" checked={config.production}
                    onChange={e => setConfig({...config, production: e.target.checked})} />
                </label>
              </div>
            </div>

            <div className="form-control mt-4">
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
              <textarea className="textarea textarea-bordered font-mono text-xs h-32"
                placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                value={config.cert_pem}
                onChange={e => setConfig({...config, cert_pem: e.target.value})} />
            </div>
          </div>
        </div>
      </div>

      {/* Info sobre tablas requeridas */}
      {!companyId && !isLoading && (
        <div className="alert alert-info shadow-sm text-sm">
          <AlertCircle size={18}/>
          <span>No se encontró un perfil de empresa. Completa los datos y guarda para crear uno nuevo.</span>
        </div>
      )}
    </div>
  );
};

export default Configuracion;
