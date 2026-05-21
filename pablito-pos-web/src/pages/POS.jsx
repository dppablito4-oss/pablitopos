import React, { useState, useEffect, useRef } from 'react';
import { Search, Plus, Trash2, Receipt, Minus, Printer, AlertTriangle, Send } from 'lucide-react';
import { useCartStore, EMISION_TYPES, PRINT_FORMATS } from '../store/useCartStore';
import { supabase } from '../lib/supabase';
import { generarHashSunat } from '../lib/sunatService';
import { useNrusValve } from '../hooks/useNrusValve';
import PrintReceipt from '../components/PrintReceipt';
import { getWhatsAppLink } from '../lib/whatsapp';

const POS = () => {
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [customerPhone, setCustomerPhone] = useState('');
  const [dbError, setDbError] = useState(null);
  const [company, setCompany] = useState(null);
  
  const { cart, emisionType, printFormat, lastReceipt, setEmisionType, setPrintFormat, setLastReceipt, addItem, removeItem, updateQuantity, clearCart, getTotals } = useCartStore();
  const { subtotal, igv, total, itemCount } = getTotals();

  // Válvula NRUS
  const { isDangerZone, isExceeded, limit, isLoading: nrusLoading } = useNrusValve(parseFloat(total));

  useEffect(() => {
    fetchProducts();
    fetchCompany();
  }, []);

  const fetchCompany = async () => {
    try {
      const { data } = await supabase.from('company_profile').select('*').eq('is_active', true).limit(1).single();
      if (data) setCompany(data);
    } catch (e) {
      console.error("Error loading company profile:", e);
    }
  };

  // Validar y forzar cambio si NRUS excede
  useEffect(() => {
    if (isExceeded && emisionType === EMISION_TYPES.BOLETA) {
      setEmisionType(EMISION_TYPES.NOTA);
    }
  }, [isExceeded, emisionType, setEmisionType]);

  const fetchProducts = async () => {
    setIsLoading(true);
    setDbError(null);
    const { data, error } = await supabase.from('products').select('*').eq('active', true).order('name').limit(200);
    if (error) {
      setDbError('No se pudo conectar a la base de datos: ' + error.message);
      setProducts([]);
    } else {
      setProducts(data || []);
    }
    setIsLoading(false);
  };

  // Obtener número correlativo de venta
  const getNextNumber = async (series) => {
    const { data } = await supabase
      .from('sales')
      .select('number')
      .eq('series', series)
      .order('number', { ascending: false })
      .limit(1)
      .single();
    return data ? (parseInt(data.number) + 1) : 1;
  };

  const filteredProducts = products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()));

  const handleEmitir = async () => {
    if (cart.length === 0) return;
    setIsProcessing(true);
    try {
      const isBoleta = emisionType === EMISION_TYPES.BOLETA;
      const isNota = emisionType === EMISION_TYPES.NOTA;
      const isAdelanto = emisionType === EMISION_TYPES.ADELANTO;
      const isCotizacion = emisionType === EMISION_TYPES.COTIZACION;

      // Determinar serie y calcular número correlativo
      const series = isBoleta ? 'B001' : isCotizacion ? 'PRF' : isAdelanto ? 'ADL' : 'NV01';
      const nextNumber = await getNextNumber(series);

      // Cálculo de totales correcto (IGV incluido en precio)
      const totalFloat = parseFloat(total);
      const subtotalBase = isBoleta ? (totalFloat / 1.18) : totalFloat;
      const igvAmt = isBoleta ? (totalFloat - subtotalBase) : 0;

      // 1. Guardar Venta en Supabase
      const { data: saleData, error: saleError } = await supabase
        .from('sales')
        .insert([{
          series,
          number: nextNumber,
          subtotal: parseFloat(subtotalBase.toFixed(2)),
          igv: parseFloat(igvAmt.toFixed(2)),
          total: totalFloat,
          company_id: company?.id || 1,
          is_proforma: isCotizacion,
          is_adelanto: isAdelanto,
        }])
        .select().single();

      if (saleError) throw saleError;

      // 2. Guardar Items
      const saleItems = cart.map(item => ({
        sale_id: saleData.id, product_id: item.id, description: item.name, quantity: item.quantity, unit_price: item.price, subtotal: item.subtotal
      }));
      const { error: itemsError } = await supabase.from('sale_items').insert(saleItems);
      if (itemsError) throw itemsError;

      // 3. Llamar API SUNAT SOLO si es Boleta
      let hashSunat = null;
      let sunatMsg = null;
      if (isBoleta) {
        try {
          hashSunat = await generarHashSunat(saleData, saleItems);
          if (hashSunat) {
            await supabase.from('sales').update({ serial_seguridad: hashSunat }).eq('id', saleData.id);
          }
        } catch (sunatErr) {
          console.warn("SUNAT no disponible, venta guardada sin hash:", sunatErr.message);
          sunatMsg = sunatErr.message;
          // La venta ya se guardó en Supabase, no bloqueamos por SUNAT
        }
      }

      // 4. Preparar datos para imprimir
      const receiptData = {
        company: { 
          ruc: company?.ruc || "20000000001", 
          razonSocial: company?.name || "PABLITO POS",
          direccion: company?.address || "AV PRINCIPAL S/N"
        },
        cliente: { numDoc: "00000000", rznSocial: "CLIENTE VARIOS" },
        serie: saleData.series,
        correlativo: saleData.number,
        fechaEmision: saleData.datetime || new Date().toISOString(),
        hash: hashSunat,
        sunatWarning: sunatMsg
      };
      setLastReceipt(receiptData);

      // Esperar un render tick para que el PrintReceipt exista en el DOM
      setTimeout(() => {
        window.print();
        clearCart();
      }, 500);

    } catch (error) {
      console.error("Error procesando venta:", error);
      alert("Error: " + (error.message || "Hubo un error procesando la venta."));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleWhatsApp = () => {
    const link = getWhatsAppLink(customerPhone, cart, {subtotal, igv, total}, emisionType);
    window.open(link, '_blank');
  };

  return (
    <>
      <PrintReceipt cart={cart} totals={{subtotal, igv, total}} emisionType={emisionType} printFormat={printFormat} receiptData={lastReceipt} />
      
      <div className="h-full flex flex-col md:flex-row gap-6 no-print">
        {/* PANEL IZQUIERDO: CATÁLOGO */}
        <div className="flex-1 flex flex-col bg-base-100 rounded-xl shadow-sm border border-base-200 overflow-hidden">
          <div className="p-4 border-b border-base-200 flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
              <input type="text" placeholder="Buscar producto..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="input input-bordered w-full pl-10" />
            </div>
          </div>
          <div className="flex-1 p-4 overflow-y-auto bg-base-200/50">
            {dbError ? (
              <div className="flex items-center justify-center h-full p-6">
                <div className="alert alert-error max-w-md">
                  <AlertTriangle size={20}/>
                  <span>{dbError}</span>
                </div>
              </div>
            ) : isLoading ? (
              <div className="flex items-center justify-center h-full"><span className="loading loading-spinner text-primary"></span></div>
            ) : products.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-base-content/40 gap-2">
                <p className="font-medium">No hay productos activos.</p>
                <p className="text-sm">Agrega productos desde el módulo Productos.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredProducts.map((p) => (
                  <div key={p.id} onClick={() => addItem(p)} className="card bg-base-100 shadow-sm hover:shadow-md cursor-pointer border border-base-200 hover:border-primary">
                    <div className="card-body p-4 items-center text-center">
                      <h2 className="card-title text-sm line-clamp-2">{p.name}</h2>
                      <p className="text-lg font-bold text-primary">S/ {p.price.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* PANEL DERECHO: CARRITO */}
        <div className="w-full md:w-96 flex flex-col gap-4">
          <div className="bg-base-100 rounded-xl shadow-sm border border-base-200 flex flex-col overflow-hidden h-[50%]">
            <div className="p-4 border-b border-base-200 bg-base-200/30 flex justify-between">
              <h2 className="font-bold text-lg">Carrito</h2>
              <span className="badge badge-primary">{itemCount} items</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {cart.map((item) => (
                <div key={item.id} className="flex flex-col p-3 border-b border-base-200 gap-2">
                  <div className="flex justify-between items-start">
                    <span className="font-medium text-sm">{item.name}</span>
                    <button onClick={() => removeItem(item.id)} className="text-error"><Trash2 size={16} /></button>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <div className="flex items-center gap-2 border border-base-300 rounded">
                      <button onClick={() => updateQuantity(item.id, item.quantity - 1)} className="px-2 py-1 bg-base-200"><Minus size={14}/></button>
                      <span className="text-sm font-semibold w-4 text-center">{item.quantity}</span>
                      <button onClick={() => updateQuantity(item.id, item.quantity + 1)} className="px-2 py-1 bg-base-200"><Plus size={14}/></button>
                    </div>
                    <span className="font-bold text-primary">S/ {item.subtotal.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* PANEL CONFIGURACIÓN Y TOTALES */}
          <div className="bg-base-100 rounded-xl shadow-sm border border-base-200 flex flex-col overflow-hidden h-[50%] flex-shrink-0">
            <div className="p-4 flex-1 overflow-y-auto space-y-4">
              
              {/* NRUS Warning */}
              {!nrusLoading && isDangerZone && (
                <div className={`alert ${isExceeded ? 'alert-error' : 'alert-warning'} text-xs p-2`}>
                  <AlertTriangle size={16} />
                  <span>{isExceeded ? '¡Límite NRUS excedido! Boleta deshabilitada.' : `Alerta NRUS: Acercándose al límite de S/${limit}`}</span>
                </div>
              )}

              {/* Controles de Emisión y Formato */}
              <div className="grid grid-cols-2 gap-2">
                <select className="select select-bordered select-sm w-full" value={emisionType} onChange={(e) => setEmisionType(e.target.value)}>
                  <option value={EMISION_TYPES.BOLETA} disabled={isExceeded}>{EMISION_TYPES.BOLETA}</option>
                  <option value={EMISION_TYPES.NOTA}>{EMISION_TYPES.NOTA}</option>
                  <option value={EMISION_TYPES.ADELANTO}>{EMISION_TYPES.ADELANTO}</option>
                  <option value={EMISION_TYPES.COTIZACION}>{EMISION_TYPES.COTIZACION}</option>
                </select>
                
                <select className="select select-bordered select-sm w-full" value={printFormat} onChange={(e) => setPrintFormat(e.target.value)}>
                  <option value={PRINT_FORMATS.TICKET}>Ticket 80mm</option>
                  <option value={PRINT_FORMATS.A4}>Formato A4</option>
                </select>
              </div>

              {/* Input WhatsApp */}
              <div className="flex gap-2">
                <input type="text" placeholder="Teléfono para WhatsApp..." value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} className="input input-bordered input-sm flex-1" />
                <button onClick={handleWhatsApp} disabled={cart.length === 0} className="btn btn-sm btn-success text-white"><Send size={16}/></button>
              </div>

              {/* Totales */}
              <div className="space-y-1 text-sm border-t border-base-200 pt-2">
                <div className="flex justify-between"><span className="text-base-content/70">Subtotal</span><span>S/ {subtotal}</span></div>
                {emisionType === EMISION_TYPES.BOLETA && <div className="flex justify-between"><span className="text-base-content/70">IGV (18%)</span><span>S/ {igv}</span></div>}
                <div className="flex justify-between items-center pt-2 font-bold text-lg"><span>Total</span><span className="text-primary">S/ {total}</span></div>
              </div>
            </div>

            <div className="p-4 border-t border-base-200">
              <button onClick={handleEmitir} disabled={cart.length === 0 || isProcessing} className="btn btn-primary w-full btn-lg">
                {isProcessing ? <span className="loading loading-spinner"></span> : <><Printer size={24} /> Cobrar e Imprimir</>}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default POS;
