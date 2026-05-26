import React, { useState, useEffect } from 'react';
import { Search, DollarSign, Plus, X, RefreshCw, ChevronDown, ChevronUp, CheckSquare, Trash2, UserSearch } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { logAudit } from '../services/auditService';
import { useCompany } from '../contexts/CompanyContext';

const Fiados = () => {
  const { company } = useCompany();
  const [fiados, setFiados] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [itemsCache, setItemsCache] = useState({});
  const [paymentsCache, setPaymentsCache] = useState({});
  const [abonoModal, setAbonoModal] = useState(null);
  const [abonoAmount, setAbonoAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('efectivo');
  const [saving, setSaving] = useState(false);
  const [createModal, setCreateModal] = useState(false);
  const [fiadoClients, setFiadoClients] = useState([]);
  const [fiadoClientSearch, setFiadoClientSearch] = useState('');
  const [fiadoSelectedClient, setFiadoSelectedClient] = useState(null);
  const [showFiadoClientDD, setShowFiadoClientDD] = useState(false);
  const [fiadoItems, setFiadoItems] = useState([{ description: '', quantity: 1, unit_price: 0 }]);

  useEffect(() => {
    if (company) {
      fetchFiados();
    }
  }, [company]);

  const fetchFiados = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data, error } = await supabase
        .from('fiados')
        .select(`*, clients(full_name, dni, phone)`)
        .order('created_at', { ascending: false });
      if (error) { setError(error.message); }
      else { setFiados(data || []); }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Error de conexión');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchItems = async (fiadoId) => {
    if (itemsCache[fiadoId]) return;
    const { data } = await supabase
      .from('fiado_items')
      .select('*')
      .eq('fiado_id', fiadoId);
    setItemsCache(prev => ({ ...prev, [fiadoId]: data || [] }));
  };

  const fetchPayments = async (fiadoId) => {
    const { data } = await supabase
      .from('fiado_payments')
      .select('*')
      .eq('fiado_id', fiadoId)
      .order('created_at', { ascending: false });
    setPaymentsCache(prev => ({ ...prev, [fiadoId]: data || [] }));
  };

  const toggleExpand = (id) => {
    if (expandedId === id) { setExpandedId(null); }
    else { 
      setExpandedId(id); 
      fetchItems(id); 
      fetchPayments(id);
    }
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
    setPaymentMethod('efectivo');
  };

  const handleAbono = async () => {
    const monto = parseFloat(abonoAmount);
    if (!monto || monto <= 0) return alert('Ingresa un monto válido.');
    if (monto > abonoModal.pendiente) return alert(`El monto no puede superar lo pendiente: S/ ${abonoModal.pendiente.toFixed(2)}`);
    setSaving(true);
    try {
      // 1. Registrar el pago en el historial de pagos
      const { error: pError } = await supabase.from('fiado_payments').insert([{
        fiado_id: abonoModal.fiadoId,
        amount: monto,
        payment_method: paymentMethod
      }]);
      if (pError) throw pError;

      // 2. Obtener fiado actual y actualizar totales
      const { data: fData, error: fGetError } = await supabase.from('fiados').select('*').eq('id', abonoModal.fiadoId).single();
      if (fGetError) throw fGetError;

      const nuevoPagado = parseFloat(fData.total_pagado) + monto;
      const nuevoPendiente = parseFloat(fData.total_bruto) - nuevoPagado;
      const nuevoStatus = nuevoPendiente <= 0 ? 'pagado' : 'pendiente';

      const { error: fUpdateError } = await supabase.from('fiados').update({
        total_pagado: nuevoPagado,
        total_pendiente: Math.max(0, nuevoPendiente),
        status: nuevoStatus,
        updated_at: new Date().toISOString(),
      }).eq('id', abonoModal.fiadoId);
      if (fUpdateError) throw fUpdateError;

      logAudit('FIADO_ABONO', `${abonoModal.code} | Abono: S/${monto.toFixed(2)} vía ${paymentMethod}`);
      setAbonoModal(null);
      fetchFiados();
    } catch (error) {
      console.error(error);
      alert('Error registrando abono: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleMarcarPagado = async (f) => {
    const pendiente = parseFloat(f.total_pendiente);
    if (pendiente <= 0) return;

    const method = prompt(`¿Con qué método de pago cancela el saldo de S/ ${pendiente.toFixed(2)}?\nEscribe: efectivo, yape, plin, o tarjeta:`, 'efectivo');
    if (method === null) return; // cancelado por usuario

    const validMethods = ['efectivo', 'yape', 'plin', 'tarjeta'];
    const selectedMethod = method.trim().toLowerCase();
    if (!validMethods.includes(selectedMethod)) {
      return alert('Método no válido. Debe ser: efectivo, yape, plin, o tarjeta.');
    }

    setSaving(true);
    try {
      // 1. Insertar el abono final
      const { error: pError } = await supabase.from('fiado_payments').insert([{
        fiado_id: f.id,
        amount: pendiente,
        payment_method: selectedMethod
      }]);
      if (pError) throw pError;

      // 2. Marcar como pagado
      const { error: fError } = await supabase.from('fiados').update({
        total_pagado: parseFloat(f.total_bruto),
        total_pendiente: 0,
        status: 'pagado',
        updated_at: new Date().toISOString(),
      }).eq('id', f.id);
      if (fError) throw fError;

      logAudit('FIADO_PAGADO', `${f.code} | Cancelado vía ${selectedMethod} | ${f.clients?.full_name}`);
      fetchFiados();
    } catch (err) {
      console.error(err);
      alert('Error al liquidar fiado: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  // === CREAR FIADO ===
  const openCreateModal = () => {
    supabase.from('clients').select('id, dni, full_name, phone').order('full_name').then(({ data }) => { if (data) setFiadoClients(data); });
    setFiadoSelectedClient(null); setFiadoClientSearch('');
    setFiadoItems([{ description: '', quantity: 1, unit_price: 0 }]);
    setCreateModal(true);
  };
  const addFiadoItem = () => setFiadoItems([...fiadoItems, { description: '', quantity: 1, unit_price: 0 }]);
  const removeFiadoItem = (i) => setFiadoItems(fiadoItems.filter((_, idx) => idx !== i));
  const updateFiadoItem = (i, field, val) => { const u = [...fiadoItems]; u[i] = { ...u[i], [field]: val }; setFiadoItems(u); };
  const fiadoNewTotal = fiadoItems.reduce((s, i) => s + (parseFloat(i.quantity) || 0) * (parseFloat(i.unit_price) || 0), 0);

  const handleCreateFiado = async () => {
    if (!fiadoSelectedClient) return alert('Selecciona un cliente.');
    const valid = fiadoItems.filter(i => i.description.trim() && parseFloat(i.quantity) > 0 && parseFloat(i.unit_price) > 0);
    if (valid.length === 0) return alert('Agrega al menos un item válido.');
    setSaving(true);
    try {
      const { data: last } = await supabase.from('fiados').select('code').like('code', 'FD-%').order('created_at', { ascending: false }).limit(1).single();
      const num = last ? parseInt(last.code.replace('FD-', '')) + 1 : 1;
      const code = `FD-${String(num).padStart(4, '0')}`;
      const tot = valid.reduce((s, i) => s + parseFloat(i.quantity) * parseFloat(i.unit_price), 0);
      const { data: fd, error: e1 } = await supabase.from('fiados').insert([{
        code, client_id: fiadoSelectedClient.id, total_bruto: parseFloat(tot.toFixed(2)),
        total_pagado: 0, total_pendiente: parseFloat(tot.toFixed(2)), status: 'pendiente'
      }]).select().single();
      if (e1) throw e1;
      const items = valid.map(i => ({
        fiado_id: fd.id, description: i.description.toUpperCase(),
        quantity: parseFloat(i.quantity), unit_price: parseFloat(i.unit_price),
        subtotal: parseFloat((parseFloat(i.quantity) * parseFloat(i.unit_price)).toFixed(2)), status: 'pendiente'
      }));
      const { error: e2 } = await supabase.from('fiado_items').insert(items);
      if (e2) throw e2;
      logAudit('FIADO_CREADO', `${code} | ${fiadoSelectedClient.full_name} | S/${tot.toFixed(2)}`);
      setCreateModal(false);
      fetchFiados();
    } catch (e) { alert('Error: ' + e.message); }
    setSaving(false);
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
        <div className="flex gap-2">
          <button className="btn btn-ghost btn-sm" onClick={fetchFiados}><RefreshCw size={16} /> Actualizar</button>
          <button className="btn btn-primary btn-sm" onClick={openCreateModal}><Plus size={16} /> Nuevo Fiado</button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-col md:flex-row gap-3">
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
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Columna Izquierda: Items del Fiado */}
                            <div>
                              <p className="text-xs text-base-content/60 font-semibold uppercase tracking-wide mb-2">Items del fiado</p>
                              {itemsCache[f.id] ? (
                                itemsCache[f.id].length === 0 ? (
                                  <p className="text-sm text-base-content/40">Sin items registrados.</p>
                                ) : (
                                  <div className="overflow-x-auto">
                                    <table className="table table-xs w-full">
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
                                  </div>
                                )
                              ) : <span className="loading loading-spinner loading-sm"/>}
                            </div>

                            {/* Columna Derecha: Historial de Abonos */}
                            <div>
                              <p className="text-xs text-base-content/60 font-semibold uppercase tracking-wide mb-2">Historial de Abonos (Pagos)</p>
                              {paymentsCache[f.id] ? (
                                paymentsCache[f.id].length === 0 ? (
                                  <p className="text-xs text-base-content/40 py-4 text-center bg-base-300/10 rounded-xl">No se han registrado abonos para este fiado.</p>
                                ) : (
                                  <div className="overflow-x-auto">
                                    <table className="table table-xs w-full">
                                      <thead><tr><th>Fecha</th><th>Método de Pago</th><th className="text-right">Monto</th></tr></thead>
                                      <tbody>
                                        {paymentsCache[f.id].map(p => (
                                          <tr key={p.id} className="hover:bg-base-300/10">
                                            <td>{new Date(p.created_at).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })}</td>
                                            <td className="capitalize font-medium">{p.payment_method}</td>
                                            <td className="text-right font-bold text-success">S/ {parseFloat(p.amount).toFixed(2)}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )
                              ) : <span className="loading loading-spinner loading-sm"/>}
                            </div>
                          </div>
                          <p className="text-xs text-base-content/40 mt-4 pt-2 border-t border-base-300/30">Creado: {new Date(f.created_at).toLocaleString('es-PE')}</p>
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
            <div className="form-control mb-3">
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
            <div className="form-control">
              <label className="label"><span className="label-text font-semibold">Método de Pago</span></label>
              <select 
                className="select select-bordered w-full font-semibold"
                value={paymentMethod}
                onChange={e => setPaymentMethod(e.target.value)}
              >
                <option value="efectivo">💵 Efectivo</option>
                <option value="yape">📲 Yape</option>
                <option value="plin">💠 Plin</option>
                <option value="tarjeta">💳 Tarjeta</option>
              </select>
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

      {/* Modal Crear Fiado */}
      {createModal && (
        <div className="modal modal-open">
          <div className="modal-box w-full max-w-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg">Nuevo Fiado</h3>
              <button className="btn btn-sm btn-circle btn-ghost" onClick={() => setCreateModal(false)}><X size={18}/></button>
            </div>

            {/* Cliente */}
            <div className="form-control mb-4">
              <label className="label"><span className="label-text font-semibold">Cliente *</span></label>
              <div className="relative">
                <UserSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" size={16} />
                <input type="text" placeholder="Buscar por nombre o DNI..." value={fiadoClientSearch}
                  onChange={(e) => { setFiadoClientSearch(e.target.value); setShowFiadoClientDD(true); if (!e.target.value) setFiadoSelectedClient(null); }}
                  onFocus={() => setShowFiadoClientDD(true)}
                  onBlur={() => setTimeout(() => setShowFiadoClientDD(false), 200)}
                  className="input input-bordered w-full pl-10" />
                {showFiadoClientDD && fiadoClientSearch && (
                  <div className="absolute z-50 top-full left-0 right-0 bg-base-100 border border-base-300 rounded-lg shadow-lg mt-1 max-h-40 overflow-y-auto">
                    {fiadoClients.filter(c => c.full_name?.toLowerCase().includes(fiadoClientSearch.toLowerCase()) || c.dni?.includes(fiadoClientSearch)).slice(0, 8).map(c => (
                      <button key={c.id} className="w-full text-left px-3 py-2 hover:bg-base-200 text-sm flex justify-between"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => { setFiadoSelectedClient(c); setFiadoClientSearch(c.full_name); setShowFiadoClientDD(false); }}>
                        <span className="font-medium">{c.full_name}</span>
                        <span className="text-base-content/50 font-mono text-xs">{c.dni || '\u2014'}</span>
                      </button>
                    ))}
                    {fiadoClients.filter(c => c.full_name?.toLowerCase().includes(fiadoClientSearch.toLowerCase()) || c.dni?.includes(fiadoClientSearch)).length === 0 && (
                      <p className="text-sm text-base-content/40 text-center py-2">Sin resultados</p>
                    )}
                  </div>
                )}
              </div>
              {fiadoSelectedClient && <p className="text-xs text-success mt-1">\u2713 {fiadoSelectedClient.full_name} \u2014 {fiadoSelectedClient.dni || 'Sin DNI'}</p>}
            </div>

            {/* Items */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold text-sm">Items del fiado</span>
                <button className="btn btn-xs btn-primary" onClick={addFiadoItem}><Plus size={14}/> Agregar</button>
              </div>
              <div className="overflow-x-auto">
                <table className="table table-sm w-full">
                  <thead><tr><th>Descripción</th><th className="w-20">Cant.</th><th className="w-24">P. Unit.</th><th className="w-24">Subtotal</th><th className="w-10"></th></tr></thead>
                  <tbody>
                    {fiadoItems.map((item, i) => (
                      <tr key={i}>
                        <td><input type="text" className="input input-sm input-bordered w-full" placeholder="Descripción..." value={item.description} onChange={e => updateFiadoItem(i, 'description', e.target.value)} /></td>
                        <td><input type="number" min="1" className="input input-sm input-bordered w-full" value={item.quantity} onChange={e => updateFiadoItem(i, 'quantity', e.target.value)} /></td>
                        <td><input type="number" min="0" step="0.01" className="input input-sm input-bordered w-full" value={item.unit_price} onChange={e => updateFiadoItem(i, 'unit_price', e.target.value)} /></td>
                        <td className="font-bold text-primary">S/ {((parseFloat(item.quantity)||0) * (parseFloat(item.unit_price)||0)).toFixed(2)}</td>
                        <td>{fiadoItems.length > 1 && <button className="btn btn-xs btn-ghost text-error" onClick={() => removeFiadoItem(i)}><Trash2 size={14}/></button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Total */}
            <div className="text-right font-bold text-lg border-t border-base-200 pt-3 mb-2">
              Total: <span className="text-primary">S/ {fiadoNewTotal.toFixed(2)}</span>
            </div>

            <div className="modal-action">
              <button className="btn btn-ghost" onClick={() => setCreateModal(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={handleCreateFiado} disabled={saving}>
                {saving ? <span className="loading loading-spinner loading-sm"/> : <><Plus size={16}/> Crear Fiado</>}
              </button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => setCreateModal(false)}></div>
        </div>
      )}
    </div>
  );
};

export default Fiados;
