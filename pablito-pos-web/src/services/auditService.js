import { supabase } from '../lib/supabase';

/**
 * Registra una acción en la tabla audit_logs de Supabase.
 * No lanza errores para no interrumpir el flujo principal.
 */
export const logAudit = async (action, detail = null) => {
  try {
    const { data: { user } } = await supabase.auth.getUser();
    await supabase.from('audit_logs').insert([{
      action,
      detail,
      user_pc: user?.email || 'sistema'
    }]);
  } catch (e) {
    console.warn('Audit log failed:', e.message);
  }
};
