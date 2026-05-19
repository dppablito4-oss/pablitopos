import React, { useState, useEffect } from 'react';
import { Search, FileText, Eye } from 'lucide-react';

const Historial = () => {
  const [ventas, setVentas] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Placeholder para la carga de ventas desde Supabase
    setVentas([
      { id: 1, series: 'B001', number: 123, datetime: '2026-05-18T10:30:00', client: 'Juan Perez', total: 13.50, is_proforma: false },
      { id: 2, series: 'P001', number: 45, datetime: '2026-05-18T11:15:00', client: 'Maria Gomez', total: 45.00, is_proforma: true },
    ]);
  }, []);

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Historial de Ventas</h2>
      </div>

      <div className="bg-base-100 p-4 rounded-xl shadow-sm flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
          <input 
            type="text" 
            placeholder="Buscar por cliente, serie o número..." 
            className="input input-bordered w-full pl-10"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <select className="select select-bordered w-full max-w-xs">
          <option>Todos los tipos</option>
          <option>Boletas</option>
          <option>Facturas</option>
          <option>Proformas</option>
        </select>
      </div>

      <div className="bg-base-100 rounded-xl shadow-sm flex-1 overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Comprobante</th>
                <th>Fecha/Hora</th>
                <th>Cliente</th>
                <th>Tipo</th>
                <th>Total</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {ventas.map((venta) => (
                <tr key={venta.id} className="hover">
                  <td className="font-mono font-medium">{venta.series}-{String(venta.number).padStart(6, '0')}</td>
                  <td>{new Date(venta.datetime).toLocaleString()}</td>
                  <td>{venta.client}</td>
                  <td>
                    {venta.is_proforma ? (
                      <span className="badge badge-warning">Proforma</span>
                    ) : (
                      <span className="badge badge-success">Venta</span>
                    )}
                  </td>
                  <td className="font-bold">S/ {venta.total.toFixed(2)}</td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn btn-sm btn-ghost"><Eye size={16} /></button>
                      <button className="btn btn-sm btn-ghost text-error"><FileText size={16} /></button>
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

export default Historial;
