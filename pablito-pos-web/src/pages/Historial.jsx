import React, { useState, useEffect } from 'react';
import { FileText, Building2, User, ShoppingCart, Loader2, Search, Printer, Send, ChevronDown, ChevronUp, Eye, RefreshCw, Download } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { generarHashSunat } from '../lib/sunatService';
import PrintReceipt from '../components/PrintReceipt';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { useCompany, REGIME_CONFIG } from '../contexts/CompanyContext';

const FILTER_TYPES = [
  { label: 'Todos', value: 'all' },
  { label: 'Boletas / Notas', value: 'ventas' },
  { label: 'Proformas', value: 'proformas' },
  { label: 'Adelantos', value: 'adelantos' },
];

const Historial = () => {
  const [ventas, setVentas] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [itemsCache, setItemsCache] = useState({});
  const { company } = useCompany();

  // Estados para impresión
  const [receiptToPrint, setReceiptToPrint] = useState(null);
  const [printFormat, setPrintFormat] = useState('TICKET');
  const [downloadPdfTrigger, setDownloadPdfTrigger] = useState(false);

  useEffect(() => {
    if (company) {
      fetchVentas();
    }
  }, [company]);

  useEffect(() => {
    if (!downloadPdfTrigger || !receiptToPrint) return;

    const generarPDF = async () => {
      // Esperar a que React renderice el componente oculto
      await new Promise(r => setTimeout(r, 800));

      const element = document.getElementById('historial-print-receipt');
      if (!element) {
        console.error('No se encontró el elemento historial-print-receipt');
        setDownloadPdfTrigger(false);
        return;
      }

      try {
        // 1. Capturar el HTML como imagen con html2canvas
        // Usamos onclone para limpiar colores oklch() que html2canvas no soporta
        const scaleVal = 4;
        const canvas = await html2canvas(element, {
          scale: scaleVal,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff',
          onclone: (clonedDoc) => {
            const allElements = clonedDoc.querySelectorAll('*');
            allElements.forEach(el => {
              const style = el.style;
              const computed = clonedDoc.defaultView.getComputedStyle(el);
              const color = computed.color;
              const bgColor = computed.backgroundColor;
              const borderColor = computed.borderColor;
              
              if (color && color.includes('oklch')) {
                style.color = '#000000';
              }
              if (bgColor && bgColor.includes('oklch')) {
                style.backgroundColor = 'transparent';
              }
              if (borderColor && borderColor.includes('oklch')) {
                style.borderColor = '#cccccc';
              }
            });
          }
        });

        const imgData = canvas.toDataURL('image/png');
        
        // Medidas físicas reales del elemento en píxeles de pantalla
        const originalWidth = element.offsetWidth || (printFormat === 'TICKET' ? 302 : 794);
        const originalHeight = element.offsetHeight || (canvas.height / scaleVal);

        const isTicketFormat = printFormat === 'TICKET';
        
        let pdf;
        if (isTicketFormat) {
          // El ticket térmico tiene 80mm de ancho. 
          // Calculamos la altura en mm proporcionalmente al contenido real del elemento.
          const pxToMm = 80 / originalWidth;
          const ticketHeightMm = originalHeight * pxToMm + 5; // +5mm margen de seguridad de salida
          pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: [80, ticketHeightMm],
          });
          pdf.addImage(imgData, 'PNG', 0, 0, 80, originalHeight * pxToMm);
        } else {
          pdf = new jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4',
          });
          const pdfWidth = pdf.internal.pageSize.getWidth();
          const pdfHeight = pdf.internal.pageSize.getHeight();
          
          // Ancho de A4 es 210mm. Usamos un margen de 10mm a cada lado, ancho útil = 190mm.
          const margin = 10;
          const targetWidth = pdfWidth - (margin * 2);
          const targetHeight = (originalHeight * targetWidth) / originalWidth;
          
          pdf.addImage(imgData, 'PNG', margin, margin, targetWidth, targetHeight);
        }

        // 5. Generar nombre de archivo y descargar
        const v = receiptToPrint;
        const fileName = `${company?.ruc || 'RUC'}-${v.series?.startsWith('F') ? '01' : '03'}-${v.series}-${String(v.number).padStart(8, '0')}.pdf`;
        pdf.save(fileName);
      } catch (err) {
        console.error('Error generando PDF:', err);
        alert('Error al generar el PDF: ' + err.message);
      } finally {
        setDownloadPdfTrigger(false);
      }
    };

    generarPDF();
  }, [downloadPdfTrigger, receiptToPrint, company]);

  const fetchVentas = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data, error } = await supabase
        .from('sales')
        .select(`*, clients(full_name, dni)`)
        .order('datetime', { ascending: false })
        .limit(200);
      if (error) { setError(error.message); }
      else { setVentas(data || []); }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Error de conexión');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchItems = async (saleId) => {
    if (itemsCache[saleId]) return;
    const { data } = await supabase
      .from('sale_items')
      .select('*')
      .eq('sale_id', saleId);
    setItemsCache(prev => ({ ...prev, [saleId]: data || [] }));
  };

  const toggleExpand = (id) => {
    if (expandedId === id) { setExpandedId(null); }
    else { setExpandedId(id); fetchItems(id); }
  };

  const filtered = ventas.filter(v => {
    const clientName = v.clients?.full_name?.toLowerCase() || '';
    const serie = `${v.series}-${v.number}`.toLowerCase();
    const matchSearch = clientName.includes(searchTerm.toLowerCase()) || serie.includes(searchTerm.toLowerCase());
    if (!matchSearch) return false;
    if (filterType === 'proformas') return v.is_proforma;
    if (filterType === 'adelantos') return v.is_adelanto;
    if (filterType === 'ventas') return !v.is_proforma && !v.is_adelanto;
    return true;
  });

  const downloadBase64File = (base64Data, filename, contentType) => {
    if (!base64Data) return;
    const linkSource = `data:${contentType};base64,${base64Data}`;
    const downloadLink = document.createElement('a');
    downloadLink.href = linkSource;
    downloadLink.download = filename;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
  };

  const handleReenviar = async (sale) => {
    setIsSending(true);
    try {
      const { data: items } = await supabase.from('sale_items').select('*').eq('sale_id', sale.id);
      if (!items || items.length === 0) {
        alert('No hay items para enviar.');
        return;
      }
      const sunatRes = await generarHashSunat(sale, items);
      if (sunatRes && sunatRes.hash) {
        await supabase.from('sales').update({ 
          serial_seguridad: sunatRes.hash,
          xml_base64: sunatRes.xml_base64,
          cdr_base64: sunatRes.cdr_base64
        }).eq('id', sale.id);
        alert('Documento reenviado y aceptado por SUNAT exitosamente.');
        fetchVentas();
      }
    } catch (e) {
      alert('Error enviando a SUNAT: ' + e.message);
    } finally {
      setIsSending(false);
    }
  };

  const getTipoBadge = (v) => {
    if (v.is_proforma) return <span className="badge badge-warning">Proforma</span>;
    if (v.is_adelanto) return <span className="badge badge-info">Adelanto</span>;
    if (v.series?.startsWith('F')) return <span className="badge badge-primary">Factura</span>;
    if (v.series?.startsWith('B')) return <span className="badge badge-success">Boleta</span>;
    return <span className="badge badge-neutral">Nota Venta</span>;
  };

  const totalHoy = ventas
    .filter(v => {
      const hoy = new Date().toDateString();
      return new Date(v.datetime).toDateString() === hoy && !v.is_proforma;
    })
    .reduce((sum, v) => sum + parseFloat(v.total || 0), 0);

  const handleReprint = async (v, format) => {
    let items = itemsCache[v.id];
    if (!items) {
      const { data } = await supabase.from('sale_items').select('*').eq('sale_id', v.id);
      items = data || [];
      setItemsCache(prev => ({ ...prev, [v.id]: items }));
    }
    
    const emisionType = v.series?.startsWith('B') ? 'Boleta Electrónica' 
                      : v.series?.startsWith('F') ? 'Factura Electrónica' 
                      : v.is_proforma ? 'Proforma' : 'Nota de Venta';

    const receiptData = {
      company: { 
        ruc: company?.ruc || "20000000001", 
        razonSocial: company?.name || "PABLITO POS",
        direccion: company?.address || "AV PRINCIPAL S/N",
        logo_base64: company?.logo_base64 || null
      },
      cliente: v.clients 
        ? { numDoc: v.clients.dni || "00000000", rznSocial: v.clients.full_name }
        : { numDoc: "00000000", rznSocial: "CLIENTE VARIOS" },
      serie: v.series,
      correlativo: v.number,
      fechaEmision: v.datetime,
      hash: v.serial_seguridad
    };

    setReceiptToPrint({ 
      ...v, 
      emisionType, 
      receiptData, 
      cart: items.map(i => ({ name: i.description, quantity: i.quantity, price: parseFloat(i.unit_price), subtotal: parseFloat(i.subtotal) })),
      totals: { subtotal: parseFloat(v.subtotal).toFixed(2), igv: parseFloat(v.igv).toFixed(2), total: parseFloat(v.total).toFixed(2) }
    });
    
    if (format === 'A4_DOWNLOAD' || format === 'TICKET_DOWNLOAD') {
      setPrintFormat(format === 'TICKET_DOWNLOAD' ? 'TICKET' : 'A4');
      setDownloadPdfTrigger(true);
    } else {
      setPrintFormat(format);
      setTimeout(() => {
        const fileName = `${company?.ruc || 'RUC'}-${v.series?.startsWith('F') ? '01' : '03'}-${v.series}-${String(v.number).padStart(8,'0')}`;
        const originalTitle = document.title;
        document.title = fileName;
        window.print();
        setTimeout(() => { document.title = originalTitle; }, 1000);
      }, 500);
    }
  };

  return (
    <>
      <div className="flex flex-col h-full gap-4 print:hidden">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Historial de Ventas</h2>
          <p className="text-base-content/60 text-sm">{ventas.length} registros · Ventas hoy: <span className="font-bold text-success">S/ {totalHoy.toFixed(2)}</span></p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={fetchVentas}>
          <RefreshCw size={16} /> Actualizar
        </button>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
          <input
            type="text"
            placeholder="Buscar por cliente o comprobante..."
            className="input input-bordered w-full pl-10"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {FILTER_TYPES.map(f => (
            <button key={f.value}
              className={`btn btn-sm ${filterType === f.value ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setFilterType(f.value)}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card flex-1 overflow-hidden flex flex-col">
        {error && <div className="alert alert-error m-4"><span>Error: {error}</span></div>}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        ) : (
          <div className="overflow-x-auto flex-1">
            <table className="table table-zebra w-full">
              <thead>
                <tr>
                  <th>Comprobante</th>
                  <th>Fecha / Hora</th>
                  <th>Cliente</th>
                  <th>Tipo</th>
                  <th className="text-right">Total</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={6} className="text-center text-base-content/50 py-12">
                    <FileText size={40} className="mx-auto mb-2 opacity-30" />
                    {searchTerm ? 'Sin resultados.' : 'No hay ventas registradas aún.'}
                  </td></tr>
                ) : filtered.map((v) => (
                  <React.Fragment key={v.id}>
                    <tr className="hover">
                      <td className="font-mono font-bold">{v.series}-{String(v.number).padStart(8, '0')}</td>
                      <td className="text-sm">{new Date(v.datetime).toLocaleString('es-PE')}</td>
                      <td>{v.clients?.full_name || <span className="text-base-content/40">Cliente varios</span>}</td>
                      <td>{getTipoBadge(v)}</td>
                      <td className="text-right font-bold text-primary">S/ {parseFloat(v.total).toFixed(2)}</td>
                      <td>
                        <div className="flex gap-1">
                          <button className="btn btn-sm btn-ghost" onClick={() => toggleExpand(v.id)}>
                            {expandedId === v.id ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
                            <Eye size={16}/>
                          </button>
                          {(v.series?.startsWith('B') || v.series?.startsWith('F')) && !v.serial_seguridad && (
                            <button 
                              className="btn btn-sm btn-warning text-white" 
                              onClick={() => handleReenviar(v)} 
                              title="Reenviar a SUNAT"
                              disabled={isSending}
                            >
                              <Send size={16} />
                            </button>
                          )}
                          <div className="dropdown dropdown-end">
                            <label tabIndex={0} className="btn btn-sm btn-ghost text-info" title="Imprimir Comprobante">
                              <Printer size={16}/>
                            </label>
                            <ul tabIndex={0} className="dropdown-content z-50 menu p-2 shadow bg-base-100 rounded-box w-48">
                              <li className="menu-title"><span>Imprimir directo</span></li>
                              <li><a onClick={() => handleReprint(v, 'TICKET')}>Ticket (80mm)</a></li>
                              <li><a onClick={() => handleReprint(v, 'A4')}>Formato A4</a></li>
                            </ul>
                          </div>
                          <div className="dropdown dropdown-end">
                            <label tabIndex={0} className="btn btn-sm btn-ghost text-primary font-bold" title="Descargar PDF">
                              PDF
                            </label>
                            <ul tabIndex={0} className="dropdown-content z-50 menu p-2 shadow bg-base-100 rounded-box w-48">
                              <li className="menu-title"><span>Descargar archivo PDF</span></li>
                              <li><a onClick={() => handleReprint(v, 'TICKET_DOWNLOAD')}><Download size={14}/> Ticket (80mm)</a></li>
                              <li><a onClick={() => handleReprint(v, 'A4_DOWNLOAD')}><Download size={14}/> Formato A4</a></li>
                            </ul>
                          </div>
                          {v.xml_base64 && (
                            <button 
                              className="btn btn-sm btn-ghost text-success font-bold" 
                              onClick={() => downloadBase64File(v.xml_base64, `${company?.ruc || 'RUC'}-${v.series}-${v.number}.xml`, 'application/xml')} 
                              title="Descargar XML"
                            >
                              XML
                            </button>
                          )}
                          {v.cdr_base64 && (
                            <button 
                              className="btn btn-sm btn-ghost text-primary font-bold" 
                              onClick={() => downloadBase64File(v.cdr_base64, `R-${company?.ruc || 'RUC'}-${v.series}-${v.number}.zip`, 'application/zip')} 
                              title="Descargar CDR (ZIP)"
                            >
                              CDR
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {expandedId === v.id && (
                      <tr className="bg-base-200/50">
                        <td colSpan={6} className="p-4">
                          <div className="flex flex-col gap-2">
                            <p className="text-xs text-base-content/60 font-semibold uppercase tracking-wide">Detalle de items</p>
                            {itemsCache[v.id] ? (
                              <table className="table table-xs w-full max-w-xl">
                                <thead><tr><th>Descripción</th><th>Cant.</th><th>P. Unit.</th><th>Subtotal</th></tr></thead>
                                <tbody>
                                  {itemsCache[v.id].map(item => (
                                    <tr key={item.id}>
                                      <td>{item.description}</td>
                                      <td>{item.quantity}</td>
                                      <td>S/ {parseFloat(item.unit_price).toFixed(2)}</td>
                                      <td>S/ {parseFloat(item.subtotal).toFixed(2)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            ) : (
                              <span className="loading loading-spinner loading-sm"/>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
    
    {/* Componente Oculto para Descarga PDF (Fuera de pantalla) */}
    {receiptToPrint && downloadPdfTrigger && (
      <div data-theme="" style={{ position: 'absolute', top: '200vh', left: 0, width: '100vw', pointerEvents: 'none', color: '#000000', backgroundColor: '#ffffff' }}>
        <div id="historial-print-receipt" style={{ width: printFormat === 'TICKET' ? '302px' : '794px', margin: '0 auto', backgroundColor: '#ffffff', color: '#000000' }}>
          <PrintReceipt 
            cart={receiptToPrint.cart} 
            totals={receiptToPrint.totals} 
            emisionType={receiptToPrint.emisionType} 
            printFormat={printFormat} 
            receiptData={receiptToPrint.receiptData}
            regimeConfig={REGIME_CONFIG[company?.tax_regime || 'nrus']}
            isPreview={true}
          />
        </div>
      </div>
    )}

    {/* Componente Oculto para Impresión de Navegador (window.print) */}
    {receiptToPrint && !downloadPdfTrigger && (
      <PrintReceipt 
        cart={receiptToPrint.cart} 
        totals={receiptToPrint.totals} 
        emisionType={receiptToPrint.emisionType} 
        printFormat={printFormat} 
        receiptData={receiptToPrint.receiptData}
        regimeConfig={REGIME_CONFIG[company?.tax_regime || 'nrus']}
        isPreview={false}
      />
    )}
  </>
  );
};

export default Historial;
