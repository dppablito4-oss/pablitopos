import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { CheckCircle, XCircle, FileText, Building2, User, ShoppingCart, Loader2, Search, Download, Printer, Camera, AlertTriangle } from 'lucide-react';
import PrintReceipt from '../components/PrintReceipt';
import { Html5Qrcode } from 'html5-qrcode';
import html2pdf from 'html2pdf.js';

const Verificacion = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [sale, setSale] = useState(null);
  const [items, setItems] = useState([]);
  const [company, setCompany] = useState(null);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorType, setErrorType] = useState(null); // 'NOT_FOUND', 'FRAUD', o mensaje normal
  const [errorMessage, setErrorMessage] = useState('');
  
  // Estado para el formulario manual y escáner
  const [isManualSearch, setIsManualSearch] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [form, setForm] = useState({
    ruc: '', tipo: '03', serie: '', correlativo: '', fecha: '', total: ''
  });

  const urlRuc = searchParams.get('ruc');
  const urlSerie = searchParams.get('serie');
  const urlCorrelativo = searchParams.get('correlativo');

  useEffect(() => {
    if (urlSerie && urlCorrelativo) {
      verificarPorUrl();
    } else {
      setIsManualSearch(true);
      setLoading(false);
    }
  }, [urlSerie, urlCorrelativo]);

  // ======= ESCÁNER QR =======
  useEffect(() => {
    let html5QrCode = null;
    
    if (showScanner) {
      // Retraso mínimo para asegurar que el div #qr-reader ya esté en el DOM
      setTimeout(() => {
        html5QrCode = new Html5Qrcode("qr-reader");
        
        html5QrCode.start(
          { facingMode: "environment" }, // Usa cámara trasera por defecto
          { fps: 10, qrbox: { width: 250, height: 250 } },
          (decodedText) => {
            // Éxito: detiene la cámara y procesa
            html5QrCode.stop().then(() => {
              setShowScanner(false);
              handleQRScanned(decodedText);
            }).catch(e => console.log('Error stopping scanner', e));
          },
          (err) => {
            // Ignorar errores de lectura en vivo (frames vacíos)
          }
        ).catch((err) => {
          console.error("Error iniciando cámara", err);
          alert("Error: Por favor, permite el acceso a la cámara en tu navegador.");
          setShowScanner(false);
        });
      }, 100);
    }
    
    return () => {
      if (html5QrCode && html5QrCode.isScanning) {
        html5QrCode.stop().catch(e => console.log('Error clearing scanner', e));
      }
    };
  }, [showScanner]);

  const handleQRScanned = async (text) => {
    const partes = text.split('|');
    if (partes.length >= 7) {
      // SUNAT format: RUC|TIPO_DOC|SERIE|CORRELATIVO|IGV|TOTAL|FECHA|TIPO_DOC_CLIENTE|NUM_DOC_CLIENTE|HASH|
      const qRuc = partes[0];
      const qTipo = partes[1];
      const qSerie = partes[2];
      const qCorrelativo = partes[3];
      const qTotal = partes[5];
      const qFecha = partes[6];
      const qHash = partes[9] || null;
      
      setForm({
        ruc: qRuc, tipo: qTipo, serie: qSerie, correlativo: qCorrelativo, fecha: qFecha, total: qTotal
      });
      await buscarComprobante(qSerie, qCorrelativo, qFecha, qTotal, qHash);
    } else {
      setErrorType('ERROR');
      setErrorMessage('El código QR escaneado no tiene un formato válido de SUNAT.');
      setIsManualSearch(true);
    }
  };

  const verificarPorUrl = async () => {
    setLoading(true);
    await buscarComprobante(urlSerie, urlCorrelativo);
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!form.serie || !form.correlativo || !form.fecha || !form.total) {
      setErrorType('ERROR');
      setErrorMessage('Por favor, completa todos los campos para la búsqueda.');
      return;
    }
    setLoading(true);
    await buscarComprobante(form.serie.toUpperCase(), form.correlativo, form.fecha, form.total);
  };

  const buscarComprobante = async (bSerie, bCorrelativo, bFecha = null, bTotal = null, bHash = null) => {
    setLoading(true);
    setErrorType(null);
    setErrorMessage('');
    
    try {
      // 1. Buscar la venta base en Supabase (El Búnker de Verdad)
      let query = supabase
        .from('sales')
        .select('*')
        .eq('series', bSerie)
        .eq('number', Number(bCorrelativo))
        .order('id', { ascending: false })
        .limit(1);

      const { data: saleData, error: saleErr } = await query.maybeSingle();

      if (saleErr) {
        setErrorType('ERROR');
        setErrorMessage(`Error de base de datos: ${saleErr.message}`);
        setLoading(false);
        return;
      }
      
      if (!saleData) {
        // Estado 3: Inexistente (Fake)
        setErrorType('NOT_FOUND');
        setLoading(false);
        return;
      }

      // 2. Validación Cruzada (Algoritmo de Match de Seguridad)
      let isManipulated = false;

      if (bFecha && bTotal) {
        // Para la fecha comparamos la fecha UTC formateada a local si es necesario, 
        // pero la base de datos la retorna en formato ISO. 
        // HTML form.fecha es YYYY-MM-DD. 
        // Asumimos que podemos parsear y comparar la parte de la fecha ignorando zona horaria estricta, 
        // o mejor, solo comparamos la fecha cruda si se guardó como string, o comparamos Totales primero.
        
        // Validación estricta de Total y Hash
        if (parseFloat(saleData.total) !== parseFloat(bTotal)) {
          isManipulated = true;
        }
        
        // Si nos pasaron el Hash desde el QR, lo validamos también
        if (bHash && saleData.serial_seguridad && bHash !== saleData.serial_seguridad) {
          isManipulated = true;
        }
      }

      if (isManipulated) {
        // Estado 2: Intento de Cutra / Alerta
        setErrorType('FRAUD');
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
      setErrorType('ERROR');
      setErrorMessage('Error al consultar el comprobante: ' + e.message);
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
          <p style={{ color: '#94a3b8' }}>Verificando comprobante de forma segura...</p>
        </div>
      </div>
    );
  }

  // ====== ESTADO 2: FRAUDE (Manipulado) ======
  if (errorType === 'FRAUD') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-red-950">
        <div className="max-w-md w-full bg-red-900/50 border border-red-500 rounded-2xl p-8 text-center shadow-2xl shadow-red-900/50">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-red-500/20 mb-6 animate-pulse">
            <AlertTriangle size={48} className="text-red-500" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-4">¡ALERTA DE SEGURIDAD!</h1>
          <p className="text-red-200 mb-8 text-lg font-medium">
            Los datos de este código QR o ingresados no coinciden con los registros oficiales de la empresa. Posible manipulación detectada.
          </p>
          <button className="btn btn-outline border-red-400 text-red-200 hover:bg-red-500 hover:text-white hover:border-red-500 w-full" 
                  onClick={() => { setErrorType(null); setIsManualSearch(true); }}>
            Consultar otro comprobante
          </button>
        </div>
      </div>
    );
  }

  // ====== ESTADO 3: INEXISTENTE ======
  if (errorType === 'NOT_FOUND' && !isManualSearch) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
        style={{ background: 'linear-gradient(180deg, #11111b 0%, #181825 100%)' }}>
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full mb-6"
            style={{ background: 'rgba(239, 68, 68, 0.1)', border: '2px solid rgba(239, 68, 68, 0.3)' }}>
            <XCircle size={40} style={{ color: '#ef4444' }} />
          </div>
          <h1 className="text-2xl font-bold mb-3" style={{ color: '#f1f5f9' }}>Comprobante Inexistente</h1>
          <p className="text-sm mb-6" style={{ color: '#64748b' }}>
            El comprobante consultado no se encuentra registrado en nuestro sistema oficial.
          </p>
          <button className="btn btn-outline btn-primary" onClick={() => { setErrorType(null); setIsManualSearch(true); }}>
            Realizar nueva búsqueda
          </button>
        </div>
      </div>
    );
  }

  // ====== FORMULARIO DE BÚSQUEDA MANUAL Y ESCÁNER ======
  if (isManualSearch && !sale) {
    return (
      <div className="min-h-screen p-4 flex items-center justify-center"
        style={{ background: 'linear-gradient(180deg, #11111b 0%, #181825 100%)' }}>
        
        {/* MODAL DEL ESCÁNER */}
        {showScanner && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="bg-base-100 p-6 rounded-2xl max-w-md w-full border border-dashed border-primary/50 relative shadow-2xl shadow-primary/20">
              <button onClick={() => setShowScanner(false)} className="absolute top-4 right-4 text-base-content/50 hover:text-white z-10">
                <XCircle size={24} />
              </button>
              <h3 className="text-xl font-bold mb-4 text-center">Escanear Código QR</h3>
              <div id="qr-reader" className="w-full bg-black rounded-xl overflow-hidden"></div>
              <p className="text-xs text-center text-base-content/50 mt-4">Apunta tu cámara al código QR impreso en el ticket.</p>
            </div>
          </div>
        )}

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

          <button 
            type="button" 
            onClick={() => setShowScanner(true)}
            className="btn btn-outline btn-secondary w-full mb-6 border-dashed border-2 hover:border-solid hover:shadow-[0_0_15px_rgba(217,70,239,0.3)] transition-all flex gap-2">
            <Camera size={20} /> ESCANEAR QR FÍSICO
          </button>
          
          <div className="divider text-xs text-base-content/40 mb-6">O INGRESA MANUALMENTE</div>

          {(errorType === 'NOT_FOUND' || errorType === 'ERROR' || errorMessage) && (
            <div className="alert alert-error text-sm mb-4 py-2">
              <XCircle size={16}/> {errorMessage || 'El comprobante consultado no se encuentra registrado en nuestro sistema oficial.'}
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
  // ====== ESTADO 1: ÉXITO TOTAL (VERIFICADO) ======
  const getFileNameBase = () => {
    return `${company?.ruc || urlRuc || 'RUC'}-${sale.series.startsWith('F') ? '01' : '03'}-${sale.series}-${String(sale.number).padStart(8,'0')}`;
  };

  const handleDownloadXML = () => {
    if (!sale.xml_base64) return alert('El XML de este comprobante no está disponible o aún no ha sido firmado.');
    const link = document.createElement('a');
    link.href = `data:text/xml;base64,${sale.xml_base64}`;
    link.download = `${getFileNameBase()}.xml`;
    link.click();
  };

  const handlePrint = () => {
    const originalTitle = document.title;
    document.title = getFileNameBase();
    window.print();
    setTimeout(() => { document.title = originalTitle; }, 1000);
  };

  const handleDownloadPDF = () => {
    const element = document.getElementById('pdf-preview-content');
    if (!element) return;
    
    const opt = {
      margin:       0,
      filename:     `${getFileNameBase()}.pdf`,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true },
      jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
    };
    
    html2pdf().set(opt).from(element).save();
  };

  const receiptData = {
    company: {
      ruc: company?.ruc || urlRuc || '—',
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
              <Download size={16} /> XML
            </button>
          )}
          <div className="join">
            <button onClick={handleDownloadPDF} className="btn btn-sm btn-primary join-item">
              <Download size={16} /> Descargar PDF
            </button>
            <button onClick={handlePrint} className="btn btn-sm btn-primary join-item border-l-black/20">
              <Printer size={16} /> Imprimir
            </button>
          </div>
        </div>
      </div>

      {/* PDF Viewer Area */}
      <div className="flex-1 overflow-auto p-4 md:p-8 bg-base-300 flex justify-center items-start print:p-0 print:bg-white print:overflow-visible">
        {/* Aquí renderizamos el recibo como A4 para previsualizarlo */}
        <div id="pdf-preview-content" className="print:hidden w-full max-w-[794px] bg-white">
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
