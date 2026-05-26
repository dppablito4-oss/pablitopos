import React, { useState, useEffect, useRef } from 'react';
import { Search, Plus, Trash2, Receipt, Minus, Printer, AlertTriangle, Send, X, UserSearch } from 'lucide-react';
import { useCartStore, EMISION_TYPES, PRINT_FORMATS } from '../store/useCartStore';
import { supabase } from '../lib/supabase';
import { generarHashSunat } from '../lib/sunatService';
import { useNrusValve } from '../hooks/useNrusValve';
import PrintReceipt from '../components/PrintReceipt';
import { getWhatsAppLink } from '../lib/whatsapp';
import { logAudit } from '../services/auditService';
import { useCompany } from '../contexts/CompanyContext';

const POS = () => {
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [customerPhone, setCustomerPhone] = useState('');
  const [clienteDoc, setClienteDoc] = useState('');
  const [clienteNombre, setClienteNombre] = useState('');
  const [dbError, setDbError] = useState(null);
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientSearch, setClientSearch] = useState('');
  const [showClientDropdown, setShowClientDropdown] = useState(false);
  
  const { company, regimeConfig } = useCompany();
  const { cart, emisionType, printFormat, lastReceipt, setEmisionType, setPrintFormat, setLastReceipt, addItem, removeItem, updateQuantity, clearCart, getTotals } = useCartStore();
  const { subtotal, igv, total, itemCount } = getTotals(regimeConfig.hasIgv);

  // Válvula NRUS
  const { isDangerZone, isExceeded, limit, isLoading: nrusLoading } = useNrusValve(parseFloat(total));

  useEffect(() => {
    fetchProducts();
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      const { data, error } = await supabase.from('clients').select('id, dni, full_name, phone').order('full_name');
      if (error) throw error;
      if (data) setClients(data);
    } catch (err) {
      console.error("Error loading clients in POS:", err);
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
    try {
      const { data, error } = await supabase.from('products').select('*').eq('active', true).order('name').limit(200);
      if (error) {
        setDbError('No se pudo conectar a la base de datos: ' + error.message);
        setProducts([]);
      } else {
        setProducts(data || []);
      }
    } catch (err) {
      console.error("Error loading products in POS:", err);
      setDbError('Error de red al consultar productos.');
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredProducts = products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()));

  const handleEmitir = async () => {
    if (cart.length === 0) return;
    setIsProcessing(true);
    try {
      const isBoleta = emisionType === EMISION_TYPES.BOLETA;
      const isFactura = emisionType === EMISION_TYPES.FACTURA;
      const isNota = emisionType === EMISION_TYPES.NOTA;
      const isAdelanto = emisionType === EMISION_TYPES.ADELANTO;
      const isCotizacion = emisionType === EMISION_TYPES.COTIZACION;

      const isBoletaOrFactura = isBoleta || isFactura;
      if (isFactura && (!selectedClient?.dni || selectedClient.dni.length !== 11)) {
        if (!clienteDoc || clienteDoc.length !== 11) {
          alert("Para Factura Electrónica es obligatorio seleccionar un cliente con RUC (11 dígitos) o ingresarlo manualmente.");
          setIsProcessing(false);
          return;
        }
      }
      const series = isBoleta ? 'B001' : isFactura ? 'F001' : isCotizacion ? 'PRF' : isAdelanto ? 'ADL' : 'NV01';

      // Totales ya calculados correctamente en el store
      const totalFloat = parseFloat(total);
      const subtotalFloat = parseFloat(subtotal);
      const igvFloat = parseFloat(igv);
      
      let clientId = selectedClient?.id || null;
      if (!clientId && clienteDoc && clienteNombre) {
        const { data: existingClient } = await supabase.from('clients').select('id').eq('dni', clienteDoc).single();
        if (existingClient) {
          clientId = existingClient.id;
        } else {
          const { data: newClient } = await supabase.from('clients').insert([{ dni: clienteDoc, full_name: clienteNombre.toUpperCase() }]).select('id').single();
          if (newClient) clientId = newClient.id;
        }
      }

      // 1. Guardar Venta en Supabase
      // El número correlativo (number) ahora se autogenera atómicamente por un Trigger en Supabase
      const { data: saleData, error: saleError } = await supabase
        .from('sales')
        .insert([{
          series,
          client_id: clientId,
          subtotal: subtotalFloat,
          igv: igvFloat,
          total: totalFloat,
          client_id: selectedClient?.id || null,
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

      // 3. Descontar stock atómicamente
      for (const item of cart) {
        try {
          await supabase.rpc('decrement_stock', { p_product_id: item.id, p_quantity: item.quantity });
        } catch {
          const { data: prod } = await supabase.from('products').select('stock').eq('id', item.id).single();
          if (prod) {
            await supabase.from('products').update({ stock: Math.max(0, (prod.stock || 0) - item.quantity) }).eq('id', item.id);
          }
        }
      }
      let hashSunat = null;
      let sunatMsg = null;
      if (isBoletaOrFactura) {
        try {
          const sunatRes = await generarHashSunat(saleData, saleItems);
          if (sunatRes && sunatRes.hash) {
            hashSunat = sunatRes.hash;
            await supabase.from('sales').update({ 
              serial_seguridad: sunatRes.hash,
              xml_base64: sunatRes.xml_base64,
              cdr_base64: sunatRes.cdr_base64
            }).eq('id', saleData.id);
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
          direccion: company?.address || "AV PRINCIPAL S/N",
          logo_base64: company?.logo_base64 || null
        },
        cliente: selectedClient 
          ? { numDoc: selectedClient.dni || "00000000", rznSocial: selectedClient.full_name }
          : { numDoc: clienteDoc || "00000000", rznSocial: clienteNombre || "CLIENTE VARIOS" },
        serie: saleData.series,
        correlativo: saleData.number,
        fechaEmision: saleData.datetime || new Date().toISOString(),
        hash: hashSunat,
        sunatWarning: sunatMsg
      };
      setLastReceipt(receiptData);
      logAudit('VENTA', `${series}-${saleData.number} | S/${totalFloat} | ${selectedClient?.full_name || 'VARIOS'}`);

      // Esperar un render tick para que el PrintReceipt exista en el DOM
      setTimeout(() => {
        const fileName = `${company?.ruc || 'RUC'}-${series.startsWith('F') ? '01' : '03'}-${series}-${String(saleData.number).padStart(8,'0')}`;
        const originalTitle = document.title;
        document.title = fileName;
        window.print();
        
        setTimeout(() => { document.title = originalTitle; }, 1000);
        clearCart();
        setSelectedClient(null);
        setClientSearch('');
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
      <PrintReceipt cart={cart} totals={{subtotal, igv, total}} emisionType={emisionType} printFormat={printFormat} receiptData={lastReceipt} regimeConfig={regimeConfig} />
      
      <div className="h-full flex flex-col lg:flex-row gap-4 md:gap-6 no-print">
        {/* ═══════════ PANEL IZQUIERDO: CATÁLOGO ═══════════ */}
        <div className="flex-1 flex flex-col min-h-0 lg:min-h-full">
          {/* Search bar */}
          <div className="bg-base-200 rounded-xl p-3 mb-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" size={18} />
              <input 
                type="text" 
                placeholder="Buscar producto..." 
                value={searchTerm} 
                onChange={(e) => setSearchTerm(e.target.value)} 
                className="input input-sm md:input-md w-full pl-10 bg-base-300/50 border-0 focus:bg-base-300" 
              />
            </div>
          </div>
          
          {/* Products grid */}
          <div className="flex-1 overflow-y-auto rounded-xl bg-base-200/30 p-3 min-h-[150px] max-h-[35vh] lg:max-h-none">
            {dbError ? (
              <div className="flex items-center justify-center h-full p-4">
                <div className="alert alert-error text-sm"><AlertTriangle size={16}/><span>{dbError}</span></div>
              </div>
            ) : isLoading ? (
              <div className="flex items-center justify-center h-32"><span className="loading loading-spinner text-primary"></span></div>
            ) : products.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-base-content/40 gap-1">
                <p className="font-medium text-sm">No hay productos activos.</p>
                <p className="text-xs">Agrega productos desde el módulo Productos.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-2 md:gap-3">
                {filteredProducts.map((p) => (
                  <button 
                    key={p.id} 
                    onClick={() => addItem(p)} 
                    className="bg-base-200 hover:bg-base-300 border border-base-300/50 hover:border-primary/50 rounded-xl p-3 md:p-4 text-center transition-all duration-150 active:scale-95"
                  >
                    <p className="text-xs md:text-sm font-medium line-clamp-2 mb-1">{p.name}</p>
                    <p className="text-sm md:text-base font-bold text-primary">S/ {p.price.toFixed(2)}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ═══════════ SEPARADOR VISUAL ═══════════ */}
        <div className="hidden lg:flex items-stretch">
          <div className="w-px bg-base-300/60"></div>
        </div>
        <div className="lg:hidden">
          <div className="divider my-2 text-[10px] text-base-content/20 uppercase tracking-widest">Carrito</div>
        </div>

        {/* ═══════════ PANEL DERECHO: CARRITO + TOTALES ═══════════ */}
        <div className="w-full lg:w-[380px] flex flex-col gap-3 min-h-0">
          
          <div className="hidden lg:flex justify-between items-center px-1">
            <h2 className="font-bold text-base md:text-lg">Carrito</h2>
            <span className="badge badge-primary badge-sm">{itemCount} items</span>
          </div>
          <div className="flex lg:hidden justify-end px-1">
            <span className="badge badge-primary badge-sm">{itemCount} items</span>
          </div>

          {/* Cart items */}
          <div className="bg-base-200 rounded-xl flex-1 overflow-y-auto min-h-[100px] max-h-[25vh] lg:max-h-[35vh]">
            {cart.length === 0 ? (
              <div className="flex items-center justify-center h-full text-base-content/30 text-sm py-8">
                Agrega productos al carrito
              </div>
            ) : (
              <div className="divide-y divide-base-300/50">
                {cart.map((item) => (
                  <div key={item.id} className="p-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.name}</p>
                      <p className="text-xs text-base-content/50">S/ {item.price.toFixed(2)} c/u</p>
                    </div>
                    <div className="flex items-center gap-1 bg-base-300/50 rounded-lg">
                      <button onClick={() => updateQuantity(item.id, item.quantity - 1)} className="px-2 py-1 hover:bg-base-300 rounded-l-lg transition-colors"><Minus size={12}/></button>
                      <span className="text-xs font-bold w-6 text-center tabular-nums">{item.quantity}</span>
                      <button onClick={() => updateQuantity(item.id, item.quantity + 1)} className="px-2 py-1 hover:bg-base-300 rounded-r-lg transition-colors"><Plus size={12}/></button>
                    </div>
                    <span className="font-bold text-sm text-primary whitespace-nowrap">S/ {item.subtotal.toFixed(2)}</span>
                    <button onClick={() => removeItem(item.id)} className="text-error/60 hover:text-error transition-colors"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Separador ── */}
          <div className="divider my-0"></div>

          {/* NRUS Warning */}
          {!nrusLoading && isDangerZone && regimeConfig.monthlyLimit && (
            <div className={`alert ${isExceeded ? 'alert-error' : 'alert-warning'} text-xs p-2`}>
              <AlertTriangle size={14} />
              <span>{isExceeded ? `¡Límite ${regimeConfig.name} excedido!` : `Alerta ${regimeConfig.name}: Acercándose al límite`}</span>
            </div>
          )}

          {/* Configuración */}
          <div className="grid grid-cols-2 gap-2">
            <select className="select select-bordered select-sm w-full text-xs" value={emisionType} onChange={(e) => setEmisionType(e.target.value)}>
              <option value={EMISION_TYPES.BOLETA} disabled={isExceeded && regimeConfig.monthlyLimit}>{EMISION_TYPES.BOLETA}</option>
              {regimeConfig.canEmitFactura && <option value={EMISION_TYPES.FACTURA}>{EMISION_TYPES.FACTURA}</option>}
              <option value={EMISION_TYPES.NOTA}>{EMISION_TYPES.NOTA}</option>
              <option value={EMISION_TYPES.ADELANTO}>{EMISION_TYPES.ADELANTO}</option>
              <option value={EMISION_TYPES.COTIZACION}>{EMISION_TYPES.COTIZACION}</option>
            </select>
            
            <select className="select select-bordered select-sm w-full text-xs" value={printFormat} onChange={(e) => setPrintFormat(e.target.value)}>
              <option value={PRINT_FORMATS.TICKET}>Ticket 80mm</option>
              <option value={PRINT_FORMATS.A4}>Formato A4</option>
            </select>
          </div>

          {/* Selector de Cliente */}
          <div className="relative">
            <label className="text-[10px] text-base-content/50 font-semibold uppercase tracking-wider">Cliente</label>
            <div className="flex gap-2 mt-1">
              <div className="relative flex-1">
                <UserSearch className="absolute left-2.5 top-1/2 -translate-y-1/2 text-base-content/30" size={14} />
                <input
                  type="text"
                  placeholder="Buscar cliente..."
                  value={clientSearch}
                  onChange={(e) => {
                    setClientSearch(e.target.value);
                    setShowClientDropdown(true);
                    if (!e.target.value) setSelectedClient(null);
                  }}
                  onFocus={() => setShowClientDropdown(true)}
                  onBlur={() => setTimeout(() => setShowClientDropdown(false), 200)}
                  className="input input-bordered input-sm w-full pl-8 text-xs"
                />
                {showClientDropdown && clientSearch && (
                  <div className="absolute z-50 top-full left-0 right-0 bg-base-200 border border-base-300 rounded-xl shadow-xl mt-1 max-h-36 overflow-y-auto">
                    {clients
                      .filter(c =>
                        c.full_name?.toLowerCase().includes(clientSearch.toLowerCase()) ||
                        c.dni?.includes(clientSearch)
                      )
                      .slice(0, 6)
                      .map(c => (
                        <button
                          key={c.id}
                          className="w-full text-left px-3 py-2 hover:bg-base-300 text-xs flex justify-between items-center"
                          onMouseDown={(e) => e.preventDefault()}
                          onClick={() => {
                            setSelectedClient(c);
                            setClientSearch(c.full_name);
                            setShowClientDropdown(false);
                          }}
                        >
                          <span className="font-medium truncate">{c.full_name}</span>
                          <span className="text-base-content/40 font-mono ml-2">{c.dni || '—'}</span>
                        </button>
                      ))}
                    {clients.filter(c =>
                      c.full_name?.toLowerCase().includes(clientSearch.toLowerCase()) ||
                      c.dni?.includes(clientSearch)
                    ).length === 0 && (
                      <p className="text-xs text-base-content/30 text-center py-2">Sin resultados</p>
                    )}
                  </div>
                )}
              </div>
              {selectedClient && (
                <button className="btn btn-sm btn-ghost text-error px-2" onClick={() => { setSelectedClient(null); setClientSearch(''); }}>
                  <X size={14} />
                </button>
              )}
              <div className="flex flex-col gap-2 mt-2">
                <input type="text" placeholder="DNI o RUC (Nuevo)" value={clienteDoc} onChange={(e) => setClienteDoc(e.target.value)} className="input input-bordered input-sm w-full text-xs" />
                <input type="text" placeholder="Nombre o Razón Social (Nuevo)" value={clienteNombre} onChange={(e) => setClienteNombre(e.target.value)} className="input input-bordered input-sm w-full text-xs" />
              </div>
            </div>
            {selectedClient && (
              <p className="text-[10px] text-success mt-1">✓ {selectedClient.full_name} — {selectedClient.dni || 'Sin DNI'}</p>
            )}
          </div>

          {/* WhatsApp */}
          <div className="flex gap-2">
            <input type="text" placeholder="Teléfono WhatsApp..." value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} className="input input-bordered input-sm flex-1 text-xs" />
            <button onClick={handleWhatsApp} disabled={cart.length === 0} className="btn btn-sm btn-success text-white px-3"><Send size={14}/></button>
          </div>

          {/* ── Separador Totales ── */}
          <div className="divider my-0"></div>

          {/* Totales */}
          <div className="bg-base-200 rounded-xl p-3 space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-base-content/50">Subtotal</span>
              <span className="tabular-nums">S/ {subtotal}</span>
            </div>
            {(emisionType === EMISION_TYPES.BOLETA || emisionType === EMISION_TYPES.FACTURA) && (
              <div className="flex justify-between text-xs">
                <span className="text-base-content/50">IGV (18%)</span>
                <span className="tabular-nums">S/ {igv}</span>
              </div>
            )}
            <div className="divider my-1"></div>
            <div className="flex justify-between items-center">
              <span className="font-bold text-sm">Total</span>
              <span className="font-bold text-lg md:text-xl text-primary tabular-nums">S/ {total}</span>
            </div>
          </div>

          {/* Botón Cobrar */}
          <button 
            onClick={handleEmitir} 
            disabled={cart.length === 0 || isProcessing} 
            className="btn btn-primary w-full h-12 md:h-14 text-sm md:text-base font-semibold gap-2"
          >
            {isProcessing ? <span className="loading loading-spinner"></span> : <><Printer size={20} /> Cobrar e Imprimir</>}
          </button>
        </div>
      </div>
    </>
  );
};

export default POS;
