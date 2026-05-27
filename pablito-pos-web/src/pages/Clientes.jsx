import React, { useState, useEffect } from 'react';
import { Search, Plus, Edit, Trash2, X, Save, User } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { logAudit } from '../services/auditService';
import { useCompany } from '../contexts/CompanyContext';

const EMPTY_FORM = { dni: '', full_name: '', phone: '', email: '', address: '' };

const Clientes = () => {
  const { company } = useCompany();
  const [clientes, setClientes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState(null);

  useEffect(() => {
    if (company) {
      fetchClientes();
    }
  }, [company]);

  const fetchClientes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data, error } = await supabase
        .from('clients')
        .select('*')
        .order('full_name', { ascending: true });
      if (error) { setError(error.message); }
      else { setClientes(data || []); }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Error de conexión');
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = clientes.filter(c =>
    c.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.dni?.includes(searchTerm) ||
    c.phone?.includes(searchTerm)
  );

  const openCreate = () => { setForm(EMPTY_FORM); setEditingId(null); setModalOpen(true); };
  const openEdit = (c) => { setForm({ dni: c.dni||'', full_name: c.full_name||'', phone: c.phone||'', email: c.email||'', address: c.address||'' }); setEditingId(c.id); setModalOpen(true); };
  const closeModal = () => { setModalOpen(false); setEditingId(null); setForm(EMPTY_FORM); };

  const handleSave = async () => {
    if (!form.full_name.trim()) return alert('El nombre es obligatorio.');
    setSaving(true);
    const payload = { ...form, full_name: form.full_name.toUpperCase(), dni: form.dni.trim() };
    let err;
    if (editingId) {
      const { error } = await supabase.from('clients').update(payload).eq('id', editingId);
      err = error;
    } else {
      const { error } = await supabase.from('clients').insert([payload]);
      err = error;
    }
    setSaving(false);
    if (err) { alert('Error: ' + err.message); return; }
    const currentEditingId = editingId; // BUG-010 FIX
    closeModal();
    logAudit(currentEditingId ? 'CLIENTE_EDITADO' : 'CLIENTE_CREADO', payload.full_name);
    fetchClientes();
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    const { error } = await supabase.from('clients').delete().eq('id', deleteId);
    if (error) alert('Error al eliminar: ' + error.message);
    else logAudit('CLIENTE_ELIMINADO', `ID: ${deleteId}`);
    setDeleteId(null);
    fetchClientes();
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Gestión de Clientes</h2>
          <p className="text-base-content/60 text-sm">{clientes.length} clientes registrados</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <Plus size={20} /> Nuevo Cliente
        </button>
      </div>

      {/* Search */}
      <div className="glass-card p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
          <input
            type="text"
            placeholder="Buscar por DNI, nombre o teléfono..."
            className="input input-bordered w-full pl-10"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Table */}
      <div className="glass-card flex-1 overflow-hidden flex flex-col">
        {error && (
          <div className="alert alert-error m-4">
            <span>Error de conexión: {error}</span>
          </div>
        )}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        ) : (
          <div className="overflow-x-auto flex-1">
            <table className="table table-zebra w-full">
              <thead>
                <tr>
                  <th>DNI / RUC</th>
                  <th>Nombre Completo</th>
                  <th>Teléfono</th>
                  <th>Email</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={5} className="text-center text-base-content/50 py-12">
                    <User size={40} className="mx-auto mb-2 opacity-30" />
                    {searchTerm ? 'Sin resultados para esa búsqueda.' : 'No hay clientes registrados aún.'}
                  </td></tr>
                ) : filtered.map((c) => (
                  <tr key={c.id} className="hover">
                    <td className="font-mono">{c.dni || <span className="text-base-content/30">—</span>}</td>
                    <td className="font-medium">{c.full_name}</td>
                    <td>{c.phone || <span className="text-base-content/30">—</span>}</td>
                    <td>{c.email || <span className="text-base-content/30">—</span>}</td>
                    <td>
                      <div className="flex gap-2">
                        <button className="btn btn-sm btn-ghost text-info" onClick={() => openEdit(c)}>
                          <Edit size={16} />
                        </button>
                        <button className="btn btn-sm btn-ghost text-error" onClick={() => setDeleteId(c.id)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Crear/Editar */}
      {modalOpen && (
        <div className="modal modal-open">
          <div className="modal-box w-full max-w-lg">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg">{editingId ? 'Editar Cliente' : 'Nuevo Cliente'}</h3>
              <button className="btn btn-sm btn-circle btn-ghost" onClick={closeModal}><X size={18}/></button>
            </div>
            <div className="flex flex-col gap-3">
              <div className="form-control">
                <label className="label"><span className="label-text">DNI / RUC</span></label>
                <input type="text" maxLength={11} className="input input-bordered" placeholder="Ej: 12345678"
                  value={form.dni} onChange={e => setForm({...form, dni: e.target.value.replace(/\D/g,'')})} />
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text font-semibold">Nombre Completo *</span></label>
                <input type="text" className="input input-bordered" placeholder="Nombre completo"
                  value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value.toUpperCase()})} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="form-control">
                  <label className="label"><span className="label-text">Teléfono</span></label>
                  <input type="text" className="input input-bordered" placeholder="9XXXXXXXX"
                    value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Email</span></label>
                  <input type="email" className="input input-bordered" placeholder="correo@ejemplo.com"
                    value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
                </div>
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text">Dirección</span></label>
                <input type="text" className="input input-bordered" placeholder="Dirección"
                  value={form.address} onChange={e => setForm({...form, address: e.target.value})} />
              </div>
            </div>
            <div className="modal-action">
              <button className="btn btn-ghost" onClick={closeModal}>Cancelar</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? <span className="loading loading-spinner loading-sm"/> : <><Save size={16}/> Guardar</>}
              </button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={closeModal}></div>
        </div>
      )}

      {/* Modal Confirmar Eliminar */}
      {deleteId && (
        <div className="modal modal-open">
          <div className="modal-box max-w-sm">
            <h3 className="font-bold text-lg text-error">¿Eliminar cliente?</h3>
            <p className="py-4 text-base-content/70">Esta acción no se puede deshacer.</p>
            <div className="modal-action">
              <button className="btn btn-ghost" onClick={() => setDeleteId(null)}>Cancelar</button>
              <button className="btn btn-error" onClick={handleDelete}>Eliminar</button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => setDeleteId(null)}></div>
        </div>
      )}
    </div>
  );
};

export default Clientes;
