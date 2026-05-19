import React, { useState, useEffect } from 'react';
import { Search, FileText, Eye, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { supabase } from '../lib/supabase';

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
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [itemsCache, setItemsCache] = useState({});

  useEffect(() => { fetchVentas(); }, []);

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

  const getTipoBadge = (v) => {
    if (v.is_proforma) return <span className="badge badge-warning">Proforma</span>;
    if (v.is_adelanto) return <span className="badge badge-info">Adelanto</span>;
    if (v.is_boletin) return <span className="badge badge-secondary">Boletín</span>;
    if (v.series?.startsWith('B')) return <span className="badge badge-success">Boleta</span>;
    return <span className="badge badge-neutral">Nota Venta</span>;
  };

  const totalHoy = ventas
    .filter(v => {
      const hoy = new Date().toDateString();
      return new Date(v.datetime).toDateString() === hoy && !v.is_proforma;
    })
    .reduce((sum, v) => sum + parseFloat(v.total || 0), 0);

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
      <div className="bg-base-100 p-4 rounded-xl shadow-sm flex flex-col md:flex-row gap-3">
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
      <div className="bg-base-100 rounded-xl shadow-sm flex-1 overflow-hidden flex flex-col">
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
                      <td className="font-mono font-bold">{v.series}-{String(v.number).padStart(6, '0')}</td>
                      <td className="text-sm">{new Date(v.datetime).toLocaleString('es-PE')}</td>
                      <td>{v.clients?.full_name || <span className="text-base-content/40">Cliente varios</span>}</td>
                      <td>{getTipoBadge(v)}</td>
                      <td className="text-right font-bold text-primary">S/ {parseFloat(v.total).toFixed(2)}</td>
                      <td>
                        <button className="btn btn-sm btn-ghost" onClick={() => toggleExpand(v.id)}>
                          {expandedId === v.id ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
                          <Eye size={16}/>
                        </button>
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
                            <div className="text-xs text-base-content/50 mt-1">
                              Subtotal: S/ {parseFloat(v.subtotal).toFixed(2)} · IGV: S/ {parseFloat(v.igv).toFixed(2)} · Total: S/ {parseFloat(v.total).toFixed(2)}
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
