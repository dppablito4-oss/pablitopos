import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { Lock, Mail, Building2, User, Phone, MapPin, AlertCircle, CheckCircle, ShieldCheck, ArrowRight, ArrowLeft } from 'lucide-react';

const Registrarse = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const inviteId = searchParams.get('invite');

  // Estados de verificación de invitación
  const [verifying, setVerifying] = useState(true);
  const [inviteValid, setInviteValid] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteType, setInviteType] = useState('company');
  const [targetCompanyId, setTargetCompanyId] = useState(null);

  // Estados del Formulario
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Datos del Formulario
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    fullName: '',
    companyName: '',
    companyRuc: '',
    companyAddress: '',
    companyPhone: '',
    taxRegime: 'nrus',
  });

  // Verificar invitación al montar
  useEffect(() => {
    const verifyInvite = async () => {
      if (!inviteId) {
        setInviteError('No se proporcionó ningún código de invitación.');
        setVerifying(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('invitations')
          .select('*')
          .eq('id', inviteId)
          .single();

        if (error || !data) {
          setInviteError('El enlace de invitación no existe o es inválido.');
          setInviteValid(false);
        } else if (data.is_used) {
          setInviteError('Este enlace de invitación ya fue utilizado.');
          setInviteValid(false);
        } else if (new Date(data.expires_at) < new Date()) {
          setInviteError('Esta invitación ha expirado (validez de 24 horas).');
          setInviteValid(false);
        } else {
          setInviteValid(true);
          setInviteType(data.type || 'company');
          setTargetCompanyId(data.company_id || null);
          if (data.email) {
            setFormData(prev => ({ ...prev, email: data.email }));
          }
        }
      } catch (err) {
        console.error('Error verifying invite:', err);
        setInviteError('Error al verificar la invitación. Intenta de nuevo.');
      } finally {
        setVerifying(false);
      }
    };

    verifyInvite();
  }, [inviteId]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const nextStep = () => {
    if (step === 1) {
      if (!formData.email || !formData.password || !formData.fullName) {
        setError('Por favor completa todos los campos de tu cuenta de usuario.');
        return;
      }
      if (formData.password.length < 6) {
        setError('La contraseña debe tener al menos 6 caracteres.');
        return;
      }
      setError('');
      if (inviteType === 'cajero') {
        handleSubmit();
      } else {
        setStep(2);
      }
    }
  };

  const prevStep = () => {
    setError('');
    setStep(1);
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    if (inviteType === 'company' && (!formData.companyName || !formData.companyRuc)) {
      setError('Por favor completa el nombre y RUC de la empresa.');
      setLoading(false);
      return;
    }

    try {
      // 1. Crear el usuario en Supabase Auth
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: formData.email,
        password: formData.password,
        options: {
          data: {
            full_name: formData.fullName
          }
        }
      });

      if (authError) throw authError;
      const newUser = authData.user;
      if (!newUser) throw new Error('No se pudo crear el usuario.');

      let companyIdToBind = targetCompanyId;

      if (inviteType === 'company') {
        // 2. Crear el perfil de empresa en company_profile
        const { data: companyData, error: companyError } = await supabase
          .from('company_profile')
          .insert([{
            name: formData.companyName,
            ruc: formData.companyRuc,
            address: formData.companyAddress || null,
            phone: formData.companyPhone || null,
            tax_regime: formData.taxRegime,
            is_active: true
          }])
          .select('id')
          .single();

        if (companyError) throw companyError;
        companyIdToBind = companyData.id;
      }

      // 3. Vincular el perfil de usuario recién creado
      const { error: profileError } = await supabase
        .from('profiles')
        .update({
          company_id: companyIdToBind,
          role: inviteType === 'company' ? 'admin' : 'cajero',
          full_name: formData.fullName
        })
        .eq('id', newUser.id);

      if (profileError) throw profileError;

      // 4. Marcar la invitación como usada
      const { error: inviteUpdateError } = await supabase
        .from('invitations')
        .update({ is_used: true })
        .eq('id', inviteId);

      if (inviteUpdateError) throw inviteUpdateError;

      // Redirigir a POS o Home con login automático
      navigate('/pos');
      window.location.reload(); // Recargar para que los contextos carguen la nueva tienda

    } catch (err) {
      console.error('Error registering:', err);
      setError(err.message || 'Ocurrió un error al registrarse.');
    } finally {
      setLoading(false);
    }
  };

  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#11111b] text-base-content p-4">
        <div className="text-center space-y-4">
          <span className="loading loading-spinner loading-lg text-primary"></span>
          <p className="text-sm text-base-content/60">Verificando enlace de invitación...</p>
        </div>
      </div>
    );
  }

  if (!inviteValid) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden text-base-content"
        style={{ background: 'linear-gradient(135deg, #11111b 0%, #181825 40%, #11111b 100%)' }}>
        <div className="bg-base-200/60 border border-base-300 backdrop-blur-xl p-8 rounded-2xl max-w-md w-full text-center space-y-5">
          <AlertCircle size={56} className="mx-auto text-error" />
          <h2 className="text-xl font-bold tracking-tight">Invitación Inválida</h2>
          <p className="text-xs text-base-content/60 leading-relaxed">{inviteError}</p>
          <button 
            onClick={() => navigate('/login')}
            className="btn btn-sm btn-ghost w-full border border-base-300 rounded-xl text-xs h-9"
          >
            Volver al Inicio
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden text-base-content"
      style={{ background: 'linear-gradient(135deg, #11111b 0%, #181825 40%, #11111b 100%)' }}>
      
      <div className="bg-base-200/60 border border-base-300 backdrop-blur-xl p-8 rounded-3xl max-w-lg w-full space-y-6">
        
        {/* CABECERA */}
        <div className="text-center">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mx-auto text-primary mb-3">
            <ShieldCheck size={20} />
          </div>
          <h1 className="text-xl font-bold tracking-tight">
            {inviteType === 'cajero' ? 'Registro de Personal' : 'Registro de Nueva Tienda'}
          </h1>
          <p className="text-xs text-base-content/50 mt-1">
            {inviteType === 'cajero' 
              ? 'Crea tu cuenta de Cajero para empezar a vender.' 
              : 'Completa los pasos para activar tu facturación electrónica.'}
          </p>
        </div>

        {/* PROGRESS STEP (Solo se muestra para tiendas con 2 pasos) */}
        {inviteType === 'company' && (
          <div className="flex items-center justify-center gap-4 text-xs font-semibold py-1">
            <span className={`px-2.5 py-1 rounded-lg ${step === 1 ? 'bg-primary text-white' : 'bg-base-300 text-base-content/50'}`}>1. Cuenta</span>
            <div className="w-8 h-px bg-base-300" />
            <span className={`px-2.5 py-1 rounded-lg ${step === 2 ? 'bg-primary text-white' : 'bg-base-300 text-base-content/50'}`}>2. Tienda</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-error/10 border border-error/20 rounded-xl text-error text-xs flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          
          {/* STEP 1: ACCOUNT DETAILS */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Nombre Completo</label>
                <div className="relative">
                  <input 
                    type="text" 
                    name="fullName"
                    value={formData.fullName}
                    onChange={handleChange}
                    placeholder="Juan Pérez"
                    className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                    required
                  />
                  <User className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                </div>
              </div>

              <div>
                <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Correo Electrónico</label>
                <div className="relative">
                  <input 
                    type="email" 
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="cajero@correo.com"
                    className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                    required
                  />
                  <Mail className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                </div>
              </div>

              <div>
                <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Contraseña</label>
                <div className="relative">
                  <input 
                    type="password" 
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                    required
                  />
                  <Lock className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                </div>
              </div>

              {inviteType === 'cajero' ? (
                <button 
                  type="submit" 
                  disabled={loading}
                  className="btn btn-sm btn-primary w-full gap-2 text-xs h-9 rounded-xl font-bold mt-2"
                >
                  {loading ? (
                    <span className="loading loading-spinner loading-xs"></span>
                  ) : (
                    <CheckCircle size={14} />
                  )}
                  Completar Registro
                </button>
              ) : (
                <button 
                  type="button" 
                  onClick={nextStep}
                  className="btn btn-sm btn-primary w-full gap-2 text-xs h-9 rounded-xl font-bold mt-2"
                >
                  Siguiente Paso
                  <ArrowRight size={14} />
                </button>
              )}
            </div>
          )}

          {/* STEP 2: COMPANY DETAILS */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Razón Social</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      name="companyName"
                      value={formData.companyName}
                      onChange={handleChange}
                      placeholder="Mi Tienda S.A.C."
                      className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                      required
                    />
                    <Building2 className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                  </div>
                </div>

                <div>
                  <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">RUC de la Empresa</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      name="companyRuc"
                      value={formData.companyRuc}
                      onChange={handleChange}
                      placeholder="20123456789"
                      maxLength={11}
                      className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                      required
                    />
                    <Building2 className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Dirección Legal</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      name="companyAddress"
                      value={formData.companyAddress}
                      onChange={handleChange}
                      placeholder="Av. Universitaria 123"
                      className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                    />
                    <MapPin className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                  </div>
                </div>

                <div>
                  <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Teléfono</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      name="companyPhone"
                      value={formData.companyPhone}
                      onChange={handleChange}
                      placeholder="987654321"
                      className="input input-sm input-bordered w-full pl-9 text-xs h-9 rounded-xl"
                    />
                    <Phone className="absolute left-3 top-2.5 text-base-content/30" size={14} />
                  </div>
                </div>
              </div>

              <div>
                <label className="label text-[10px] font-bold uppercase text-base-content/40 pb-1">Régimen Tributario</label>
                <select 
                  name="taxRegime"
                  value={formData.taxRegime}
                  onChange={handleChange}
                  className="select select-sm select-bordered w-full text-xs h-9 rounded-xl"
                >
                  <option value="nrus">Nuevo RUS (NRUS) - Sin IGV ni Facturas</option>
                  <option value="rer">Régimen Especial (RER) - Con IGV y Facturas</option>
                  <option value="mype">Mype Tributario - Con IGV y Facturas</option>
                  <option value="general">Régimen General - Con IGV y Facturas</option>
                </select>
              </div>

              <div className="flex gap-2 mt-2">
                <button 
                  type="button" 
                  onClick={prevStep}
                  className="btn btn-sm btn-ghost border border-base-300 flex-1 gap-2 text-xs h-9 rounded-xl"
                >
                  <ArrowLeft size={14} />
                  Atrás
                </button>
                <button 
                  type="submit" 
                  disabled={loading}
                  className="btn btn-sm btn-primary flex-1 gap-2 text-xs h-9 rounded-xl font-bold"
                >
                  {loading ? (
                    <span className="loading loading-spinner loading-xs"></span>
                  ) : (
                    <CheckCircle size={14} />
                  )}
                  Completar Registro
                </button>
              </div>
            </div>
          )}

        </form>
      </div>

    </div>
  );
};

export default Registrarse;
