import React, { useState, useEffect } from 'react';
import { Search, DollarSign, Plus } from 'lucide-react';

const Fiados = () => {
  const [fiados, setFiados] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Placeholder para la carga de fiados desde Supabase
    setFiados([
      { id: 1, code: 'F-001', client: 'Pedro Suarez', total_bruto: 150.00, total_pagado: 50.00, total_pendiente: 100.00, status: 'pendiente' },
      { id: 2, code: 'F-002', client: 'Ana Rojas', total_bruto: 80.00, total_pagado: 80.00, total_pendiente: 0.00, status: 'pagado' },
    ]);
  }, []);

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Gestión de Fiados (Créditos)</h2>
        <button className="btn btn-primary">
          <Plus size={20} />
          Nuevo Fiado
        </button>
      </div>

      <div className="bg-base-100 p-4 rounded-xl shadow-sm flex gap-4">
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
        <select className="select select-bordered w-full max-w-xs">
          <option>Todos los estados</option>
          <option>Pendiente</option>
          <option>Pagado</option>
        </select>
      </div>

      <div className="bg-base-100 rounded-xl shadow-sm flex-1 overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Código</th>
                <th>Cliente</th>
                <th>Total Bruto</th>
                <th>Pagado</th>
                <th>Pendiente</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {fiados.map((fiado) => (
                <tr key={fiado.id} className="hover">
                  <td className="font-mono">{fiado.code}</td>
                  <td className="font-medium">{fiado.client}</td>
                  <td>S/ {fiado.total_bruto.toFixed(2)}</td>
                  <td className="text-success">S/ {fiado.total_pagado.toFixed(2)}</td>
                  <td className="text-error font-bold">S/ {fiado.total_pendiente.toFixed(2)}</td>
                  <td>
                    {fiado.status === 'pagado' ? (
                      <span className="badge badge-success">Pagado</span>
                    ) : (
                      <span className="badge badge-warning">Pendiente</span>
                    )}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn btn-sm btn-outline btn-success" disabled={fiado.status === 'pagado'}>
                        <DollarSign size={16} /> Abonar
                      </button>
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

export default Fiados;
