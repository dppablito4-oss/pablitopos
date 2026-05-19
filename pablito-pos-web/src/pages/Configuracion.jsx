import React from 'react';
import { Save } from 'lucide-react';

const Configuracion = () => {
  return (
    <div className="flex flex-col h-full gap-4 max-w-4xl mx-auto w-full">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Configuración del Sistema</h2>
        <button className="btn btn-primary">
          <Save size={20} />
          Guardar Cambios
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg border-b pb-2">Datos de la Empresa</h3>
            
            <div className="form-control w-full">
              <label className="label"><span className="label-text">Nombre / Razón Social</span></label>
              <input type="text" placeholder="Ej. Pablito POS S.A.C" className="input input-bordered w-full" defaultValue="Pablito POS" />
            </div>
            
            <div className="form-control w-full">
              <label className="label"><span className="label-text">RUC</span></label>
              <input type="text" placeholder="Ej. 20123456789" className="input input-bordered w-full" defaultValue="10123456789" />
            </div>
            
            <div className="form-control w-full">
              <label className="label"><span className="label-text">Dirección</span></label>
              <input type="text" placeholder="Dirección del local" className="input input-bordered w-full" />
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg border-b pb-2">Preferencias de Venta</h3>
            
            <div className="form-control">
              <label className="label cursor-pointer">
                <span className="label-text">Incluir IGV (18%) en los precios</span> 
                <input type="checkbox" className="toggle toggle-primary" defaultChecked />
              </label>
            </div>
            
            <div className="form-control">
              <label className="label cursor-pointer">
                <span className="label-text">Imprimir ticket automáticamente al vender</span> 
                <input type="checkbox" className="toggle toggle-primary" defaultChecked />
              </label>
            </div>

            <div className="form-control w-full mt-4">
              <label className="label"><span className="label-text">Mensaje al pie del ticket</span></label>
              <textarea className="textarea textarea-bordered h-24" placeholder="¡Gracias por su compra!"></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Configuracion;
