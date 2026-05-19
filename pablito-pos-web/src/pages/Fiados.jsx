import React, { useState, useEffect } from 'react';
import { Search, DollarSign, Plus, X, RefreshCw, ChevronDown, ChevronUp, CheckSquare, Square } from 'lucide-react';
import { supabase } from '../lib/supabase';

const Fiados = () => {
  const [fiados, setFiados] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [itemsCache, setItemsCache] = useState({});
  const [abonoModal, setAbonoModal] = useState(null); // { fiadoId, pendiente }
  const [abonoAmount, setAbonoAmount] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchFiados(); }, []);

  const fetchFiados = async () => {
    setIsLoading(true);
    setError(null);
    const { data, error } = await supabase
      .from('fiados')
      .select(`*, clients(full_name, dni, phone)`)
      .order('created_at', { ascending: false });
    if (error) { setError(error.message); }
    else { setFiados(data || []); }
    setIsLoading(false);
  };

  const fetchItems = async (fiadoId) => {
    if (itemsCache[fiadoId]) return;
    const { data } = await supabase
      .from('fiado_items')
      .select('*')
      .eq('fiado_id', fiadoId);
    setItemsCache(prev => ({ ...prev, [fiadoId]: data || [] }));
  };

  const toggleExpand = (id) => {
    if (expandedId === id) { setExpandedId(null); }
    else { setExpandedId(id); fetchItems(id); }
  };

  const filtered = fiados.filter(f => {
    const nombre = f.clients?.full_name?.toLowerCase() || '';
    const code = f.code?.toLowerCase() || '';
    const matchSearch = nombre.includes(searchTerm.toLowerCase()) || code.includes(searchTerm.toLowerCase());
    if (!matchSearch) return false;
    if (filterStatus === 'pendiente') return f.status === 'pendiente';
    if (filterStatus === 'pagado') return f.status === 'pagado';
    return true;
  });

  const totalPendiente = fiados
    .filter(f => f.status === 'pendiente')
    .reduce((sum, f) => sum + parseFloat(f.total_pendiente || 0), 0);

  const openAbono = (f) => {
    setAbonoModal({ fiadoId: f.id, pendiente: parseFloat(f.total_pendiente), code: f.code });
    setAbonoAmount('');
  };

  const handleAbono = async () => {
    const monto = parseFloat(abonoAmount);
    if (!monto || monto <= 0) return alert('Ingresa un monto válido.');
    if (monto > abonoModal.pendiente) return alert(`El monto no puede superar lo pendiente: S/ ${abonoModal.pendiente.toFixed(2)}`);
    setSaving(true);
    // Obtener fiado actual
    const { data: fData } = await supabase.from('fiados').select('*').eq('id', abonoModal.fiadoId).single();
    const nuevoPagado = parseFloat(fData.total_pagado) + monto;
    const nuevoPendiente = parseFloat(fData.total_bruto) - nuevoPagado;
    const nuevoStatus = nuevoPendiente <= 0 ? 'pagado' : 'pendiente';
    const { error } = await supabase.from('fiados').update({
      total_pagado: nuevoPagado,
      total_pendiente: Math.max(0, nuevoPendiente),
      status: nuevoStatus,
      updated_at: new Date().toISOString(),
    }).eq('id', abonoModal.fiadoId);
    setSaving(false);
    if (error) { alert('Error: ' + error.message); return; }
    setAbonoModal(null);
    fetchFiados();
  };

  const handleMarcarPagado = async (f) => {
    if (!confirm(`¿Marcar como PAGADO el fiado ${f.code} de ${f.clients?.full_name}?`)) return;
    const { error } = await supabase.from('fiados').update({
      total_pagado: parseFloat(f.total_bruto),
      total_pendiente: 0,
      status: 'pagado',
      updated_at: new Date().toISOString(),
    }).eq('id', f.id);
    if (error) alert('Error: ' + error.message);
    else fetchFiados();
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Fiados (Créditos)</h2>
          <p className="text-base-content/60 text-sm">
            Total pendiente: <span className="font-bold text-error">S/ {totalPendiente.toFixed(2)}</span>
            {' · '}{fiados.filter(f => f.status === 'pendiente').length} fiados activos
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={fetchFiados}>
          <RefreshCw size={16} /> Actualizar
        </button>
      </div>

      {/* Filters */}
      <div className="bg-base-100 p-4 rounded-xl shadow-sm flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
          <input
            type="text"
            placeholder="Buscar por cliente o código..."
            className="input input-bordered w-full pl-10"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          {[['all','Todos'],['pendiente','Pendientes'],['pagado','Pagados']].map(([val, label]) => (
            <button key={val}
              className={`btn btn-sm ${filterStatus === val ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setFilterStatus(val)}>
              {label}
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
                  <th>Código</th>
                  <th>Cliente</th>
                  <th className="text-right">Total</th>
                  <th className="text-right text-success">Pagado</th>
                  <th className="text-right text-error">Pendiente</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={7} className="text-center text-base-content/50 py-12">
                    <DollarSign size={40} className="mx-auto mb-2 opacity-30" />
                    {searchTerm ? 'Sin resultados.' : 'No hay fiados registrados.'}
                  </td></tr>
                ) : filtered.map((f) => (
                  <React.Fragment key={f.id}>
                    <tr className="hover">
                      <td className="font-mono font-bold">{f.code}</td>
                      <td>
                        <div>
                          <p className="font-medium">{f.clients?.full_name || '—'}</p>
                          {f.clients?.phone && <p className="text-xs text-base-content/50">{f.clients.phone}</p>}
                        </div>
                      </td>
                      <td className="text-right">S/ {parseFloat(f.total_bruto).toFixed(2)}</td>
                      <td className="text-right text-success font-semibold">S/ {parseFloat(f.total_pagado).toFixed(2)}</td>
                      <td className="text-right text-error font-bold">S/ {parseFloat(f.total_pendiente).toFixed(2)}</td>
                      <td>
                        {f.status === 'pagado'
                          ? <span className="badge badge-success">Pagado</span>
                          : <span className="badge badge-warning">Pendiente</span>}
                      </td>
                      <td>
                        <div className="flex gap-1">
                          <button className="btn btn-xs btn-ghost" onClick={() => toggleExpand(f.id)} title="Ver detalle">
                            {expandedId === f.id ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                          </button>
                          {f.status !== 'pagado' && (
                            <>
                              <button className="btn btn-xs btn-outline btn-success" onClick={() => openAbono(f)} title="Registrar abono">
                                <DollarSign size={13}/> Abonar
                              </button>
                              <button className="btn btn-xs btn-outline btn-primary" onClick={() => handleMarcarPagado(f)} title="Marcar todo pagado">
                                <CheckSquare size={13}/>
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                    {expandedId === f.id && (
                      <tr className="bg-base-200/50">
                        <td colSpan={7} className="p-4">
                          <p className="text-xs text-base-content/60 font-semibold uppercase tracking-wide mb-2">Items del fiado</p>
                          {itemsCache[f.id] ? (
                            itemsCache[f.id].length === 0 ? (
                              <p className="text-sm text-base-content/40">Sin items registrados.</p>
                            ) : (
                              <table className="table table-xs w-full max-w-xl">
                                <thead><tr><th>Descripción</th><th>Bloque</th><th>Cant.</th><th>P. Unit.</th><th>Subtotal</th><th>Estado</th></tr></thead>
                                <tbody>
                                  {itemsCache[f.id].map(item => (
                                    <tr key={item.id}>
                                      <td>{item.description}</td>
                                      <td>{item.block || '—'}</td>
                                      <td>{item.quantity}</td>
                                      <td>S/ {parseFloat(item.unit_price||0).toFixed(2)}</td>
                                      <td>S/ {parseFloat(item.subtotal||0).toFixed(2)}</td>
                                      <td>
                                        {item.status === 'pagado'
                                          ? <span className="badge badge-success badge-sm">Pagado</span>
                                          : <span className="badge badge-warning badge-sm">Pendiente</span>}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )
                          ) : <span className="loading loading-spinner loading-sm"/>}
                          <p className="text-xs text-base-content/40 mt-2">Creado: {new Date(f.created_at).toLocaleString('es-PE')}</p>
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

      {/* Modal Abono */}
      {abonoModal && (
        <div className="modal modal-open">
          <div className="modal-box max-w-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg">Registrar Abono</h3>
              <button className="btn btn-sm btn-circle btn-ghost" onClick={() => setAbonoModal(null)}><X size={18}/></button>
            </div>
            <p className="text-base-content/70 mb-1">Fiado: <span className="font-bold">{abonoModal.code}</span></p>
            <p className="text-base-content/70 mb-4">Pendiente: <span className="font-bold text-error">S/ {abonoModal.pendiente.toFixed(2)}</span></p>
            <div className="form-control">
              <label className="label"><span className="label-text font-semibold">Monto a abonar (S/)</span></label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                max={abonoModal.pendiente}
                className="input input-bordered input-lg text-center font-bold"
                placeholder="0.00"
                value={abonoAmount}
                onChange={e => setAbonoAmount(e.target.value)}
                autoFocus
              />
            </div>
            <div className="modal-action">
              <button className="btn btn-ghost" onClick={() => setAbonoModal(null)}>Cancelar</button>
              <button className="btn btn-success" onClick={handleAbono} disabled={saving}>
                {saving ? <span className="loading loading-spinner loading-sm"/> : <><DollarSign size={16}/> Registrar Abono</>}
              </button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => setAbonoModal(null)}></div>
        </div>
      )}
    </div>
  );
};

export default Fiados;
