import React, { useState, useEffect } from 'react';
import { Search, Plus, Edit, Trash2 } from 'lucide-react';

const Productos = () => {
  const [productos, setProductos] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Placeholder para la carga de productos desde Supabase
    setProductos([
      { id: 1, code: 'P001', name: 'Arroz costeño 1kg', unit: 'UND', price: 4.50, stock: 100 },
      { id: 2, code: 'P002', name: 'Aceite Primor 1L', unit: 'UND', price: 9.00, stock: 50 },
    ]);
  }, []);

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Gestión de Productos</h2>
        <button className="btn btn-primary">
          <Plus size={20} />
          Nuevo Producto
        </button>
      </div>

      <div className="bg-base-100 p-4 rounded-xl shadow-sm flex gap-4">
        <div className="relative flex-1">
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

      <div className="bg-base-100 rounded-xl shadow-sm flex-1 overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Unidad</th>
                <th>Precio</th>
                <th>Stock</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {productos.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.code.includes(searchTerm)).map((producto) => (
                <tr key={producto.id} className="hover">
                  <td><span className="badge badge-ghost">{producto.code}</span></td>
                  <td className="font-medium">{producto.name}</td>
                  <td>{producto.unit}</td>
                  <td>S/ {producto.price.toFixed(2)}</td>
                  <td>
                    <span className={`badge ${producto.stock < 10 ? 'badge-error' : 'badge-success'}`}>
                      {producto.stock}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn btn-sm btn-ghost text-info"><Edit size={16} /></button>
                      <button className="btn btn-sm btn-ghost text-error"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Productos;
