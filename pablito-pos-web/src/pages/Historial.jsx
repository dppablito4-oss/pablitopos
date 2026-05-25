import React, { useState, useEffect } from 'react';
import { Search, FileText, Eye, RefreshCw, ChevronDown, ChevronUp, Send, Printer } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { generarHashSunat } from '../lib/sunatService';

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
  const [company, setCompany] = useState(null);

  useEffect(() => { fetchVentas(); fetchCompany(); }, []);

  const fetchCompany = async () => {
    const { data } = await supabase.from('company_profile').select('*').eq('is_active', true).limit(1).single();
    if (data) setCompany(data);
  };

  const fetchVentas = async () => {
    setIsLoading(true);
    setError(null);
    const { data, error } = await supabase
      .from('sales')
      .select(`*, clients(full_name, dni)`)
      .order('datetime', { ascending: false })
      .limit(200);
    if (error) { setError(error.message); }
    else { setVentas(data || []); }
    setIsLoading(false);
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
    if (v.is_boletin) return <span className="badge badge-secondary">Boletín</span>;
    if (v.series?.startsWith('F')) return <span className="badge badge-primary">Factura</span>;
    if (v.series?.startsWith('B')) return <span className="badge badge-success">Boleta</span>;
    if (v.series?.startsWith('F')) return <span className="badge badge-accent">Factura</span>;
    return <span className="badge badge-neutral">Nota Venta</span>;
  };

  const totalHoy = ventas
    .filter(v => {
      const hoy = new Date().toDateString();
      return new Date(v.datetime).toDateString() === hoy && !v.is_proforma;
    })
    .reduce((sum, v) => sum + parseFloat(v.total || 0), 0);

  const handleReprint = async (v) => {
    let items = itemsCache[v.id];
    if (!items) {
      const { data } = await supabase.from('sale_items').select('*').eq('sale_id', v.id);
      items = data || [];
      setItemsCache(prev => ({ ...prev, [v.id]: items }));
    }
    const tipo = v.series?.startsWith('B') ? 'BOLETA DE VENTA ELECTR\u00d3NICA' : v.series?.startsWith('F') ? 'FACTURA ELECTR\u00d3NICA' : v.is_proforma ? 'PROFORMA' : 'NOTA DE VENTA';
    const tipoCod = v.series?.startsWith('F') ? '01' : '03';
    const filename = `${company?.ruc || '00000000000'}-${tipoCod}-${v.series}-${String(v.number).padStart(8,'0')}`;
    const html = `<html><head><title>${filename}</title>
      <style>body{font-family:monospace;max-width:320px;margin:auto;padding:20px;font-size:12px}
      table{width:100%;border-collapse:collapse}td,th{padding:3px;text-align:left;border-bottom:1px solid #ddd}
      .r{text-align:right}.c{text-align:center}.b{font-weight:bold}h2{margin:0}hr{border:1px dashed #999}</style>
      </head><body>
      <div class="c"><h2>${company?.name || 'PABLITO POS'}</h2>
      <p>RUC: ${company?.ruc || '\u2014'}</p>
      <p>${company?.address || ''}</p>
      <p class="b">${tipo}</p>
      <p class="b">${v.series}-${String(v.number).padStart(8,'0')}</p>
      <p>${new Date(v.datetime).toLocaleString('es-PE')}</p></div><hr>
      ${v.clients?.full_name ? `<p><b>Cliente:</b> ${v.clients.full_name}</p><p><b>Doc:</b> ${v.clients.dni||'\u2014'}</p>` : ''}
      <table><tr><th>Cant</th><th>Descripci\u00f3n</th><th class="r">P.U.</th><th class="r">Total</th></tr>
      ${items.map(i=>`<tr><td>${i.quantity}</td><td>${i.description}</td><td class="r">${parseFloat(i.unit_price).toFixed(2)}</td><td class="r">${parseFloat(i.subtotal).toFixed(2)}</td></tr>`).join('')}
      </table><hr>
      <p class="r">Subtotal: S/ ${parseFloat(v.subtotal).toFixed(2)}</p>
      <p class="r">IGV: S/ ${parseFloat(v.igv).toFixed(2)}</p>
      <p class="r b" style="font-size:1.3em">TOTAL: S/ ${parseFloat(v.total).toFixed(2)}</p>
      ${v.serial_seguridad ? `<p class="c" style="font-size:0.7em">Hash: ${v.serial_seguridad}</p>`:''}
      <p class="c">\u00a1Gracias por su compra!</p>
      <script>window.onload=()=>window.print();</script></body></html>`;
    const win = window.open('', '_blank');
    win.document.write(html);
    win.document.close();
  };

  return (
    <div className="flex flex-col h-full gap-4">
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
                          <button className="btn btn-sm btn-ghost text-info" onClick={() => handleReprint(v)} title="Reimprimir Ticket / Guardar PDF">
                            <Printer size={16}/>
                          </button>
                          {v.xml_base64 && (
                            <button 
                              className="btn btn-sm btn-ghost text-success" 
                              onClick={() => downloadBase64File(v.xml_base64, `${company?.ruc || 'RUC'}-${v.series}-${v.number}.xml`, 'application/xml')} 
                              title="Descargar XML"
                            >
                              XML
                            </button>
                          )}
                          {v.cdr_base64 && (
                            <button 
                              className="btn btn-sm btn-ghost text-primary" 
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
                            <div className="text-xs text-base-content/50 mt-1 flex justify-between">
                              <span>Subtotal: S/ {parseFloat(v.subtotal).toFixed(2)} · IGV: S/ {parseFloat(v.igv).toFixed(2)} · Total: S/ {parseFloat(v.total).toFixed(2)}</span>
                              {v.serial_seguridad && <span className="text-success font-mono">Hash: {v.serial_seguridad}</span>}
                            </div>
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
  );
};

export default Historial;
