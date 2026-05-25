import React, { useState, useEffect } from 'react';
import { Search, Plus, Edit, Trash2, X, Save, Package, Upload } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { logAudit } from '../services/auditService';
import * as XLSX from 'xlsx';

const EMPTY_FORM = { code: '', name: '', unit: 'UND', price: '', stock: '', active: true };

const Productos = () => {
  const [productos, setProductos] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState(null);

  useEffect(() => { fetchProductos(); }, []);

  const fetchProductos = async () => {
    setIsLoading(true);
    setError(null);
    const { data, error } = await supabase
      .from('products')
      .select('*')
      .order('name', { ascending: true });
    if (error) { setError(error.message); }
    else { setProductos(data || []); }
    setIsLoading(false);
  };

  const filtered = productos.filter(p =>
    p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.code?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const openCreate = () => { setForm(EMPTY_FORM); setEditingId(null); setModalOpen(true); };
  const openEdit = (p) => {
    setForm({ code: p.code||'', name: p.name||'', unit: p.unit||'UND', price: p.price||'', stock: p.stock||0, active: p.active });
    setEditingId(p.id); setModalOpen(true);
  };
  const closeModal = () => { setModalOpen(false); setEditingId(null); setForm(EMPTY_FORM); };

  const handleSave = async () => {
    if (!form.name.trim()) return alert('El nombre del producto es obligatorio.');
    if (!form.price || isNaN(parseFloat(form.price))) return alert('El precio debe ser un número válido.');
    setSaving(true);
    const payload = {
      code: form.code.trim().toUpperCase() || null,
      name: form.name.trim().toUpperCase(),
      unit: form.unit || 'UND',
      price: parseFloat(form.price),
      stock: parseInt(form.stock) || 0,
      active: form.active,
    };
    let err;
    if (editingId) {
      const { error } = await supabase.from('products').update(payload).eq('id', editingId);
      err = error;
    } else {
      const { error } = await supabase.from('products').insert([payload]);
      err = error;
    }
    setSaving(false);
    if (err) { alert('Error: ' + err.message); return; }
    closeModal();
    logAudit(editingId ? 'PRODUCTO_EDITADO' : 'PRODUCTO_CREADO', payload.name);
    fetchProductos();
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    const { error } = await supabase.from('products').update({ active: false }).eq('id', deleteId);
    if (error) alert('Error: ' + error.message);
    else logAudit('PRODUCTO_DESACTIVADO', `ID: ${deleteId}`);
    setDeleteId(null);
    fetchProductos();
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const bstr = evt.target.result;
        const workbook = XLSX.read(bstr, { type: 'binary' });
        const wsname = workbook.SheetNames[0];
        const ws = workbook.Sheets[wsname];
        const data = XLSX.utils.sheet_to_json(ws, { header: 1 });
        
        // Asumimos formato (Fila 1 son cabeceras): Código | Nombre | Unidad | Precio | Stock
        const newProducts = [];
        for (let i = 1; i < data.length; i++) {
          const row = data[i];
          if (!row || !row[1]) continue; // Nombre es obligatorio (Columna B / Índice 1)
          newProducts.push({
            code: row[0] ? row[0].toString().trim().toUpperCase() : null,
            name: row[1].toString().trim().toUpperCase(),
            unit: row[2] ? row[2].toString().trim().toUpperCase() : 'UND',
            price: parseFloat(row[3]) || 0,
            stock: parseInt(row[4]) || 0,
            active: true
          });
        }

        if (newProducts.length === 0) {
          alert('No se encontraron productos válidos en el archivo. Recuerda el orden: Código, Nombre, Unidad, Precio, Stock.');
          setIsLoading(false);
          return;
        }

        const { error } = await supabase.from('products').insert(newProducts);
        if (error) throw error;

        alert(`¡Se importaron ${newProducts.length} productos correctamente!`);
        logAudit('IMPORTACION_EXCEL', `${newProducts.length} productos agregados`);
        fetchProductos();
      } catch (err) {
        alert('Error al importar el archivo: ' + err.message);
        setIsLoading(false);
      }
    };
    reader.readAsBinaryString(file);
    e.target.value = null; // Resetear input
  };

  const getStockBadge = (stock) => {
    if (stock <= 0) return <span className="badge badge-error">Sin stock</span>;
    if (stock < 10) return <span className="badge badge-warning">{stock}</span>;
    return <span className="badge badge-success">{stock}</span>;
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Gestión de Productos</h2>
          <p className="text-base-content/60 text-sm">{productos.filter(p=>p.active).length} productos activos</p>
        </div>
        <div className="flex gap-2">
          <label className="btn btn-outline btn-secondary">
            <Upload size={20} />
            <span className="hidden sm:inline">Importar Excel</span>
            <input type="file" accept=".xlsx, .xls, .csv" className="hidden" onChange={handleFileUpload} />
          </label>
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={20} /> <span className="hidden sm:inline">Nuevo Producto</span>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="glass-card p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
          <input
            type="text"
            placeholder="Buscar por código o nombre..."
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
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Unidad</th>
                  <th>Precio</th>
                  <th>Stock</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={7} className="text-center text-base-content/50 py-12">
                    <Package size={40} className="mx-auto mb-2 opacity-30" />
                    {searchTerm ? 'Sin resultados para esa búsqueda.' : 'No hay productos registrados aún.'}
                  </td></tr>
                ) : filtered.map((p) => (
                  <tr key={p.id} className="hover">
                    <td><span className="badge badge-ghost font-mono">{p.code || '—'}</span></td>
                    <td className="font-medium">{p.name}</td>
                    <td>{p.unit || '—'}</td>
                    <td className="font-bold text-primary">S/ {parseFloat(p.price).toFixed(2)}</td>
                    <td>{getStockBadge(p.stock)}</td>
                    <td>
                      {p.active
                        ? <span className="badge badge-success badge-sm">Activo</span>
                        : <span className="badge badge-ghost badge-sm">Inactivo</span>}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button className="btn btn-sm btn-ghost text-info" onClick={() => openEdit(p)}>
                          <Edit size={16} />
                        </button>
                        <button className="btn btn-sm btn-ghost text-error" onClick={() => setDeleteId(p.id)}>
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
              <h3 className="font-bold text-lg">{editingId ? 'Editar Producto' : 'Nuevo Producto'}</h3>
              <button className="btn btn-sm btn-circle btn-ghost" onClick={closeModal}><X size={18}/></button>
            </div>
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="form-control">
                  <label className="label"><span className="label-text">Código</span></label>
                  <input type="text" className="input input-bordered" placeholder="Ej: P001"
                    value={form.code} onChange={e => setForm({...form, code: e.target.value})} />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Unidad</span></label>
                  <select className="select select-bordered" value={form.unit} onChange={e => setForm({...form, unit: e.target.value})}>
                    <option>UND</option><option>KG</option><option>LT</option><option>MT</option><option>CJA</option><option>DOC</option>
                  </select>
                </div>
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text font-semibold">Nombre del Producto *</span></label>
                <input type="text" className="input input-bordered" placeholder="Nombre del producto"
                  value={form.name} onChange={e => setForm({...form, name: e.target.value.toUpperCase()})} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="form-control">
                  <label className="label"><span className="label-text font-semibold">Precio (S/) *</span></label>
                  <input type="number" min="0" step="0.01" className="input input-bordered" placeholder="0.00"
                    value={form.price} onChange={e => setForm({...form, price: e.target.value})} />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Stock</span></label>
                  <input type="number" min="0" className="input input-bordered" placeholder="0"
                    value={form.stock} onChange={e => setForm({...form, stock: e.target.value})} />
                </div>
              </div>
              <div className="form-control">
                <label className="label cursor-pointer">
                  <span className="label-text">Producto activo (visible en POS)</span>
                  <input type="checkbox" className="toggle toggle-primary" checked={form.active}
                    onChange={e => setForm({...form, active: e.target.checked})} />
                </label>
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

      {/* Modal Confirmar Desactivar */}
      {deleteId && (
        <div className="modal modal-open">
          <div className="modal-box max-w-sm">
            <h3 className="font-bold text-lg text-warning">¿Desactivar producto?</h3>
            <p className="py-4 text-base-content/70">El producto quedará inactivo y no aparecerá en el POS.</p>
            <div className="modal-action">
              <button className="btn btn-ghost" onClick={() => setDeleteId(null)}>Cancelar</button>
              <button className="btn btn-warning" onClick={handleDelete}>Desactivar</button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => setDeleteId(null)}></div>
        </div>
      )}
    </div>
  );
};

export default Productos;
