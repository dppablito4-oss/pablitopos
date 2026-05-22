import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { CheckCircle, XCircle, FileText, Building2, User, ShoppingCart, Loader2 } from 'lucide-react';

const Verificacion = () => {
  const [searchParams] = useSearchParams();
  const [sale, setSale] = useState(null);
  const [items, setItems] = useState([]);
  const [company, setCompany] = useState(null);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const ruc = searchParams.get('ruc');
  const serie = searchParams.get('serie');
  const correlativo = searchParams.get('correlativo');

  useEffect(() => {
    if (serie && correlativo) {
      verificar();
    } else {
      setError('Enlace de verificación inválido. Faltan parámetros.');
      setLoading(false);
    }
  }, [serie, correlativo]);

  const verificar = async () => {
    setLoading(true);
    setError(null);
    try {
      // Buscar la venta
      const { data: saleData, error: saleErr } = await supabase
        .from('sales')
        .select('*')
        .eq('series', serie)
        .eq('number', parseInt(correlativo))
        .single();

      if (saleErr || !saleData) {
        setError('Comprobante no encontrado en el sistema.');
        setLoading(false);
        return;
      }
      setSale(saleData);

      // Buscar items, empresa y cliente en paralelo
      const [itemsRes, companyRes, clientRes] = await Promise.all([
        supabase.from('sale_items').select('*').eq('sale_id', saleData.id),
        saleData.company_id 
          ? supabase.from('company_profile').select('*').eq('id', saleData.company_id).single()
          : Promise.resolve({ data: null }),
        saleData.client_id
          ? supabase.from('clients').select('*').eq('id', saleData.client_id).single()
          : Promise.resolve({ data: null }),
      ]);

      setItems(itemsRes.data || []);
      if (companyRes.data) setCompany(companyRes.data);
      if (clientRes.data) setClient(clientRes.data);
    } catch (e) {
      setError('Error al consultar el comprobante: ' + e.message);
    }
    setLoading(false);
  };

  const getTipo = () => {
    if (!sale) return '';
    if (sale.is_proforma) return 'PROFORMA';
    if (sale.is_adelanto) return 'ADELANTO';
    if (sale.series?.startsWith('B')) return 'BOLETA DE VENTA ELECTRÓNICA';
    return 'NOTA DE VENTA';
  };

  const formatDate = (d) => {
    try { return new Date(d).toLocaleString('es-PE', { dateStyle: 'long', timeStyle: 'short' }); }
    catch { return d; }
  };

  // ====== LOADING ======
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
        style={{ background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)' }}>
        <div className="text-center">
          <Loader2 size={48} className="animate-spin mx-auto mb-4" style={{ color: '#6366f1' }} />
          <p style={{ color: '#94a3b8' }}>Verificando comprobante...</p>
        </div>
      </div>
    );
  }

  // ====== ERROR / NOT FOUND ======
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
        style={{ background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)' }}>
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full mb-6"
            style={{ background: 'rgba(239, 68, 68, 0.1)', border: '2px solid rgba(239, 68, 68, 0.3)' }}>
            <XCircle size={40} style={{ color: '#ef4444' }} />
          </div>
          <h1 className="text-2xl font-bold mb-3" style={{ color: '#f1f5f9' }}>Comprobante no encontrado</h1>
          <p className="text-sm mb-6" style={{ color: '#64748b' }}>{error}</p>
          <div className="rounded-xl p-4" style={{ background: 'rgba(30, 41, 59, 0.5)', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
            <p className="text-xs" style={{ color: '#475569' }}>
              Si crees que es un error, contacta al establecimiento emisor.
            </p>
          </div>
          <p className="text-xs mt-8" style={{ color: '#334155' }}>Pablito POS · Verificación Electrónica</p>
        </div>
      </div>
    );
  }

  // ====== COMPROBANTE VERIFICADO ======
  return (
    <div className="min-h-screen p-4 pb-12"
      style={{ background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)' }}>
      
      <div className="max-w-lg mx-auto">
        {/* Status badge */}
        <div className="text-center mb-6 pt-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
            style={{ background: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#4ade80' }}>
            <CheckCircle size={18} />
            Comprobante verificado
          </div>
        </div>

        {/* Receipt card */}
        <div className="rounded-2xl overflow-hidden"
          style={{
            background: 'linear-gradient(180deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)',
            border: '1px solid rgba(148, 163, 184, 0.1)',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.4)',
          }}>
          
          {/* Accent line */}
          <div className="h-[2px]" style={{ background: 'linear-gradient(90deg, transparent, #22c55e, #4ade80, #22c55e, transparent)' }} />

          {/* Company header */}
          <div className="px-6 pt-8 pb-6 text-center" style={{ borderBottom: '1px dashed rgba(148, 163, 184, 0.1)' }}>
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl mb-3"
              style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
              <Building2 size={24} style={{ color: '#818cf8' }} />
            </div>
            <h1 className="text-xl font-bold mb-1" style={{ color: '#f1f5f9' }}>
              {company?.name || 'EMPRESA'}
            </h1>
            <p className="text-sm" style={{ color: '#64748b' }}>RUC: {company?.ruc || ruc || '—'}</p>
            {company?.address && <p className="text-xs mt-1" style={{ color: '#475569' }}>{company.address}</p>}
          </div>

          {/* Document type & number */}
          <div className="px-6 py-5 text-center" style={{ borderBottom: '1px dashed rgba(148, 163, 184, 0.1)' }}>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg mb-2"
              style={{ background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
              <FileText size={14} style={{ color: '#818cf8' }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#a5b4fc' }}>
                {getTipo()}
              </span>
            </div>
            <p className="text-2xl font-bold font-mono tracking-wide" style={{ color: '#e2e8f0' }}>
              {sale.series}-{String(sale.number).padStart(6, '0')}
            </p>
            <p className="text-xs mt-2" style={{ color: '#64748b' }}>
              {formatDate(sale.datetime)}
            </p>
          </div>

          {/* Client info */}
          {client && (
            <div className="px-6 py-4" style={{ borderBottom: '1px dashed rgba(148, 163, 184, 0.1)' }}>
              <div className="flex items-center gap-3">
                <User size={16} style={{ color: '#64748b' }} />
                <div>
                  <p className="text-sm font-medium" style={{ color: '#cbd5e1' }}>{client.full_name}</p>
                  <p className="text-xs" style={{ color: '#64748b' }}>DNI/RUC: {client.dni || '—'}</p>
                </div>
              </div>
            </div>
          )}

          {/* Items */}
          <div className="px-6 py-5" style={{ borderBottom: '1px dashed rgba(148, 163, 184, 0.1)' }}>
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart size={14} style={{ color: '#64748b' }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>
                Detalle de productos
              </span>
            </div>
            <div className="space-y-3">
              {items.map((item, i) => (
                <div key={i} className="flex justify-between items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: '#cbd5e1' }}>{item.description}</p>
                    <p className="text-xs" style={{ color: '#64748b' }}>
                      {item.quantity} x S/ {parseFloat(item.unit_price).toFixed(2)}
                    </p>
                  </div>
                  <p className="text-sm font-bold whitespace-nowrap" style={{ color: '#e2e8f0' }}>
                    S/ {parseFloat(item.subtotal).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Totals */}
          <div className="px-6 py-5">
            <div className="space-y-2 mb-3">
              <div className="flex justify-between">
                <span className="text-sm" style={{ color: '#64748b' }}>Subtotal</span>
                <span className="text-sm" style={{ color: '#94a3b8' }}>S/ {parseFloat(sale.subtotal).toFixed(2)}</span>
              </div>
              {parseFloat(sale.igv) > 0 && (
                <div className="flex justify-between">
                  <span className="text-sm" style={{ color: '#64748b' }}>IGV (18%)</span>
                  <span className="text-sm" style={{ color: '#94a3b8' }}>S/ {parseFloat(sale.igv).toFixed(2)}</span>
                </div>
              )}
            </div>
            <div className="flex justify-between items-center pt-3" style={{ borderTop: '1px solid rgba(148, 163, 184, 0.15)' }}>
              <span className="text-lg font-bold" style={{ color: '#f1f5f9' }}>Total</span>
              <span className="text-2xl font-bold" style={{ color: '#4ade80' }}>
                S/ {parseFloat(sale.total).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Hash/security footer */}
          {sale.serial_seguridad && (
            <div className="px-6 py-4" style={{ background: 'rgba(0,0,0,0.2)', borderTop: '1px solid rgba(148, 163, 184, 0.05)' }}>
              <p className="text-xs text-center font-mono break-all" style={{ color: '#475569' }}>
                Hash: {sale.serial_seguridad}
              </p>
            </div>
          )}
        </div>

        {/* Footer branding */}
        <div className="text-center mt-8 space-y-1">
          <p className="text-xs font-medium" style={{ color: '#475569' }}>
            Verificado por Pablito POS
          </p>
          <p className="text-xs" style={{ color: '#334155' }}>
            Documento electrónico · Consulta SUNAT
          </p>
        </div>
      </div>
    </div>
  );
};

export default Verificacion;
