import React, { useState, useEffect } from 'react';
import { Search, Plus, Edit, Trash2 } from 'lucide-react';

const Clientes = () => {
  const [clientes, setClientes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  // Placeholder para la carga de clientes
  useEffect(() => {
    // Aquí iría la llamada a Supabase
    setClientes([
      { id: 1, dni: '12345678', full_name: 'Juan Perez', phone: '987654321', email: 'juan@example.com' },
      { id: 2, dni: '87654321', full_name: 'Maria Gomez', phone: '912345678', email: 'maria@example.com' },
    ]);
  }, []);

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Gestión de Clientes</h2>
        <button className="btn btn-primary">
          <Plus size={20} />
          Nuevo Cliente
        </button>
      </div>

      <div className="bg-base-100 p-4 rounded-xl shadow-sm flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
          <input 
            type="text" 
            placeholder="Buscar por DNI o Nombre..." 
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
                <th>DNI</th>
                <th>Nombre Completo</th>
                <th>Teléfono</th>
                <th>Email</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientes.filter(c => c.full_name.toLowerCase().includes(searchTerm.toLowerCase()) || c.dni.includes(searchTerm)).map((cliente) => (
                <tr key={cliente.id} className="hover">
                  <td>{cliente.dni}</td>
                  <td>{cliente.full_name}</td>
                  <td>{cliente.phone}</td>
                  <td>{cliente.email}</td>
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

export default Clientes;
