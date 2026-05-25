import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { CheckCircle, XCircle, FileText, Building2, User, ShoppingCart, Loader2, Search, Download, Printer } from 'lucide-react';
import PrintReceipt from '../components/PrintReceipt';

const Verificacion = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [sale, setSale] = useState(null);
  const [items, setItems] = useState([]);
  const [company, setCompany] = useState(null);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Estado para el formulario manual
  const [isManualSearch, setIsManualSearch] = useState(false);
  const [form, setForm] = useState({
    ruc: '', tipo: '03', serie: '', correlativo: '', fecha: '', total: ''
  });

  const ruc = searchParams.get('ruc');
  const serie = searchParams.get('serie');
  const correlativo = searchParams.get('correlativo');

  useEffect(() => {
    if (serie && correlativo) {
      verificarPorUrl();
    } else {
      setIsManualSearch(true);
      setLoading(false);
    }
  }, [serie, correlativo]);

  const verificarPorUrl = async () => {
    setLoading(true);
    await buscarComprobante(serie, correlativo);
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!form.serie || !form.correlativo || !form.fecha || !form.total) {
      setError('Por favor, completa todos los campos para la búsqueda.');
      return;
    }
    setLoading(true);
    await buscarComprobante(form.serie.toUpperCase(), form.correlativo, form.fecha, form.total);
  };

  const buscarComprobante = async (bSerie, bCorrelativo, bFecha = null, bTotal = null) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Buscar la venta base
      let query = supabase
        .from('sales')
        .select('*')
        .eq('series', bSerie)
        .eq('number', Number(bCorrelativo))
        .order('id', { ascending: false })
        .limit(1);

      const { data: saleData, error: saleErr } = await query.maybeSingle();

      if (saleErr) {
        setError(`Error de base de datos: ${saleErr.message}`);
        setLoading(false);
        return;
      }
      
      if (!saleData) {
        setError('Comprobante no encontrado en el sistema.');
        setLoading(false);
        return;
      }

      // 2. Si es búsqueda manual estricta, validar Fecha y Monto (SUNAT Rules)
      if (bFecha && bTotal) {
        const saleDate = new Date(saleData.datetime).toISOString().split('T')[0];
        if (saleDate !== bFecha || parseFloat(saleData.total) !== parseFloat(bTotal)) {
          setError('Los datos ingresados (Fecha o Monto) no coinciden con el comprobante.');
          setLoading(false);
          return;
        }
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
    if (sale.series?.startsWith('F')) return 'FACTURA ELECTRÓNICA';
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
        style={{ background: 'linear-gradient(180deg, #11111b 0%, #181825 100%)' }}>
        <div className="text-center">
          <Loader2 size={48} className="animate-spin mx-auto mb-4" style={{ color: '#6366f1' }} />
          <p style={{ color: '#94a3b8' }}>Verificando comprobante...</p>
        </div>
      </div>
    );
  }

  // ====== ERROR / NOT FOUND ======
  if (error && !isManualSearch) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
        style={{ background: 'linear-gradient(180deg, #11111b 0%, #181825 100%)' }}>
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full mb-6"
            style={{ background: 'rgba(239, 68, 68, 0.1)', border: '2px solid rgba(239, 68, 68, 0.3)' }}>
            <XCircle size={40} style={{ color: '#ef4444' }} />
          </div>
          <h1 className="text-2xl font-bold mb-3" style={{ color: '#f1f5f9' }}>Comprobante no encontrado</h1>
          <p className="text-sm mb-6" style={{ color: '#64748b' }}>{error}</p>
          <button className="btn btn-outline btn-primary" onClick={() => { setError(null); setIsManualSearch(true); }}>
            Realizar nueva búsqueda
          </button>
        </div>
      </div>
    );
  }

  // ====== FORMULARIO DE BÚSQUEDA MANUAL (SUNAT) ======
  if (isManualSearch && !sale) {
    return (
      <div className="min-h-screen p-4 flex items-center justify-center"
        style={{ background: 'linear-gradient(180deg, #11111b 0%, #181825 100%)' }}>
        <div className="max-w-md w-full rounded-2xl overflow-hidden p-6 shadow-2xl"
          style={{ background: 'rgba(30, 30, 46, 0.95)', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl mb-3"
              style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
              <Search size={24} style={{ color: '#818cf8' }} />
            </div>
            <h1 className="text-xl font-bold text-white">Consulta de Comprobantes</h1>
            <p className="text-sm text-base-content/60">Verifica la validez de tu documento electrónico</p>
          </div>

          {error && (
            <div className="alert alert-error text-sm mb-4 py-2">
              <XCircle size={16}/> {error}
            </div>
          )}

          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div className="form-control">
              <label className="label"><span className="label-text text-gray-300">RUC del Emisor</span></label>
              <input type="text" className="input input-bordered w-full bg-base-300" placeholder="Ej. 20123456789"
                value={form.ruc} onChange={e => setForm({...form, ruc: e.target.value.replace(/\D/g,'')})} maxLength={11} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="form-control">
                <label className="label"><span className="label-text text-gray-300">Tipo</span></label>
                <select className="select select-bordered bg-base-300" value={form.tipo} onChange={e => setForm({...form, tipo: e.target.value})}>
                  <option value="03">Boleta (B)</option>
                  <option value="01">Factura (F)</option>
                </select>
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text text-gray-300">Serie</span></label>
                <input type="text" className="input input-bordered bg-base-300 uppercase" placeholder="Ej. B001"
                  value={form.serie} onChange={e => setForm({...form, serie: e.target.value.toUpperCase()})} maxLength={4} />
              </div>
            </div>

            <div className="form-control">
              <label className="label"><span className="label-text text-gray-300">Número Correlativo</span></label>
              <input type="number" className="input input-bordered w-full bg-base-300" placeholder="Ej. 1"
                value={form.correlativo} onChange={e => setForm({...form, correlativo: e.target.value})} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="form-control">
                <label className="label"><span className="label-text text-gray-300">Fecha de Emisión</span></label>
                <input type="date" className="input input-bordered bg-base-300"
                  value={form.fecha} onChange={e => setForm({...form, fecha: e.target.value})} />
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text text-gray-300">Monto Total (S/)</span></label>
                <input type="number" step="0.01" className="input input-bordered bg-base-300" placeholder="0.00"
                  value={form.total} onChange={e => setForm({...form, total: e.target.value})} />
              </div>
            </div>

            <button type="submit" className="btn btn-primary w-full mt-4" disabled={loading}>
              {loading ? <Loader2 className="animate-spin" /> : 'Buscar Comprobante'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ====== COMPROBANTE VERIFICADO ======
  const handleDownloadXML = () => {
    if (!sale.xml_base64) return alert('El XML de este comprobante no está disponible o aún no ha sido firmado.');
    const link = document.createElement('a');
    link.href = `data:text/xml;base64,${sale.xml_base64}`;
    link.download = `${company?.ruc || ruc || 'RUC'}-${sale.series.startsWith('F') ? '01' : '03'}-${sale.series}-${String(sale.number).padStart(8,'0')}.xml`;
    link.click();
  };

  const handlePrint = () => {
    window.print();
  };

  const receiptData = {
    company: {
      ruc: company?.ruc || ruc || '—',
      razonSocial: company?.name || 'EMPRESA',
      direccion: company?.address || '',
      logo_base64: company?.logo_base64 || null
    },
    cliente: {
      numDoc: client?.dni || '—',
      rznSocial: client?.full_name || '—'
    },
    serie: sale.series,
    correlativo: sale.number,
    fechaEmision: sale.datetime,
    hash: sale.serial_seguridad || ''
  };

  const totals = {
    subtotal: parseFloat(sale.subtotal).toFixed(2),
    igv: parseFloat(sale.igv).toFixed(2),
    total: parseFloat(sale.total).toFixed(2)
  };

  const cart = items.map(item => ({
    name: item.description,
    quantity: item.quantity,
    price: parseFloat(item.unit_price),
    subtotal: parseFloat(item.subtotal)
  }));

  return (
    <div className="min-h-screen bg-base-300 flex flex-col">
      {/* Top Toolbar (No se imprime) */}
      <div className="bg-neutral text-neutral-content p-4 shadow-md flex flex-wrap justify-between items-center z-10 print:hidden gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-success/20 text-success px-3 py-1.5 rounded-full flex items-center gap-2 text-sm font-bold border border-success/30">
            <CheckCircle size={16} /> Verificado
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight">
              {getTipo()} {sale.series}-{String(sale.number).padStart(8, '0')}
            </h1>
            <p className="text-xs opacity-70">Consulta Pública SUNAT</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {sale.xml_base64 && (
            <button onClick={handleDownloadXML} className="btn btn-sm btn-outline btn-accent">
              <Download size={16} /> Descargar XML
            </button>
          )}
          <button onClick={handlePrint} className="btn btn-sm btn-primary">
            <Printer size={16} /> Descargar / Imprimir PDF
          </button>
        </div>
      </div>

      {/* PDF Viewer Area */}
      <div className="flex-1 overflow-auto p-4 md:p-8 bg-base-300 flex justify-center items-start print:p-0 print:bg-white print:overflow-visible">
        {/* Aquí renderizamos el recibo como A4 para previsualizarlo */}
        <div className="print:hidden w-full max-w-[794px]">
          <PrintReceipt 
            cart={cart}
            totals={totals}
            emisionType={getTipo()}
            printFormat="A4"
            receiptData={receiptData}
            regimeConfig={{}}
            isPreview={true}
          />
        </div>
        
        {/* Aquí renderizamos el componente oficial de impresión escondido para cuando se haga window.print() */}
        <div className="hidden print:block w-full">
          <PrintReceipt 
            cart={cart}
            totals={totals}
            emisionType={getTipo()}
            printFormat="A4"
            receiptData={receiptData}
            regimeConfig={{}}
            isPreview={false}
          />
        </div>
      </div>
    </div>
  );
};

export default Verificacion;
