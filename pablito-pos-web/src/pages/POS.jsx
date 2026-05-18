import { useState, useEffect } from 'react';
import { Search, Plus, Trash2, Receipt, Minus } from 'lucide-react';
import { useCartStore } from '../store/useCartStore';
import { supabase } from '../lib/supabase';
import { generateTicketPDF } from '../lib/pdfGenerator';

const POS = () => {
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  
  const cart = useCartStore((state) => state.cart);
  const addItem = useCartStore((state) => state.addItem);
  const removeItem = useCartStore((state) => state.removeItem);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const { subtotal, igv, total, itemCount } = useCartStore((state) => state.getTotals());

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    setIsLoading(true);
    const { data, error } = await supabase
      .from('products')
      .select('*')
      .eq('active', 1)
      .limit(50);
      
    if (error) {
      console.error('Error fetching products:', error);
    } else {
      if (data && data.length > 0) {
        setProducts(data);
      } else {
        // Mock data para ver la UI si no hay productos en la BD aún
        setProducts([
          { id: 1, name: 'Coca Cola 2L', price: 8.50, stock: 10 },
          { id: 2, name: 'Galletas Oreo', price: 2.00, stock: 25 },
          { id: 3, name: 'Agua San Mateo', price: 2.50, stock: 50 },
          { id: 4, name: 'Inca Kola 1.5L', price: 7.00, stock: 12 },
          { id: 5, name: 'Papas Lays', price: 3.50, stock: 30 },
          { id: 6, name: 'Cerveza Cristal', price: 6.00, stock: 40 },
        ]);
      }
    }
    setIsLoading(false);
  };

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    (p.code && p.code.includes(searchTerm))
  );

  const handleEmitir = async () => {
    if (cart.length === 0) return;
    
    setIsLoading(true);
    try {
      // 1. Guardar la Venta en Supabase
      const { data: saleData, error: saleError } = await supabase
        .from('sales')
        .insert([
          {
            series: 'B001',
            number: Math.floor(Math.random() * 1000000), // Simulado, se debe manejar un counter real
            subtotal: parseFloat(subtotal),
            igv: parseFloat(igv),
            total: parseFloat(total),
            company_id: 1 // Asegúrate de tener al menos una compañía en la BD con ID 1
          }
        ])
        .select()
        .single();

      if (saleError) throw saleError;

      // 2. Guardar los Items de la Venta
      const saleItems = cart.map(item => ({
        sale_id: saleData.id,
        product_id: item.id,
        description: item.name,
        quantity: item.quantity,
        unit_price: item.price,
        subtotal: item.subtotal
      }));

      const { error: itemsError } = await supabase
        .from('sale_items')
        .insert(saleItems);

      if (itemsError) throw itemsError;

      // 3. Generar PDF (Abre en nueva pestaña)
      generateTicketPDF(cart, { subtotal, igv, total });

      // 4. Limpiar Carrito
      useCartStore.getState().clearCart();
      alert("Venta registrada y PDF generado exitosamente!");

    } catch (error) {
      console.error("Error procesando venta:", error);
      alert("Hubo un error procesando la venta.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col md:flex-row gap-6">
      {/* Main Panel - Products */}
      <div className="flex-1 flex flex-col bg-base-100 rounded-xl shadow-sm border border-base-200 overflow-hidden">
        {/* Search Header */}
        <div className="p-4 border-b border-base-200 flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/50" size={20} />
            <input 
              type="text" 
              placeholder="Buscar producto..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input input-bordered w-full pl-10 focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
        </div>

        {/* Product Grid */}
        <div className="flex-1 p-4 overflow-y-auto bg-base-200/50">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <span className="loading loading-spinner loading-lg text-primary"></span>
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredProducts.map((p) => (
                <div 
                  key={p.id} 
                  onClick={() => addItem(p)}
                  className="card bg-base-100 shadow-sm hover:shadow-md transition-shadow border border-base-200 cursor-pointer hover:border-primary/50"
                >
                  <div className="card-body p-4 items-center text-center">
                    <h2 className="card-title text-sm line-clamp-2">{p.name}</h2>
                    <p className="text-lg font-bold text-primary">S/ {p.price.toFixed(2)}</p>
                    <p className="text-xs text-base-content/50 mt-1">Stock: {p.stock}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Side Panel - Cart */}
      <div className="w-full md:w-96 bg-base-100 rounded-xl shadow-sm border border-base-200 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-base-200 bg-base-200/30 flex justify-between items-center">
          <h2 className="font-bold text-lg flex items-center gap-2">
            <ShoppingCartIcon size={20} /> Carrito
          </h2>
          <span className="badge badge-primary font-bold">{itemCount} items</span>
        </div>

        {/* Cart Items Area */}
        <div className="flex-1 overflow-y-auto p-2">
          {cart.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-base-content/50">
              <ShoppingCartIcon size={48} className="mb-4 opacity-20" />
              <p>El carrito está vacío</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cart.map((item) => (
                <div key={item.id} className="flex flex-col p-3 bg-base-200/30 rounded-lg border border-base-200 gap-2">
                  <div className="flex justify-between items-start">
                    <span className="font-medium text-sm line-clamp-2 pr-2">{item.name}</span>
                    <button 
                      onClick={() => removeItem(item.id)}
                      className="text-error hover:bg-error/10 p-1 rounded transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <div className="flex items-center gap-2 bg-base-100 rounded-lg border border-base-300">
                      <button 
                        onClick={() => updateQuantity(item.id, item.quantity - 1)}
                        className="p-1 px-2 hover:bg-base-200 rounded-l-lg transition-colors"
                      >
                        <Minus size={14} />
                      </button>
                      <span className="text-sm font-semibold w-6 text-center">{item.quantity}</span>
                      <button 
                        onClick={() => updateQuantity(item.id, item.quantity + 1)}
                        className="p-1 px-2 hover:bg-base-200 rounded-r-lg transition-colors"
                      >
                        <Plus size={14} />
                      </button>
                    </div>
                    <span className="font-bold text-primary">S/ {item.subtotal.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cart Totals */}
        <div className="bg-base-200/50 border-t border-base-200 p-4 space-y-4">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-base-content/70">Subtotal</span>
              <span>S/ {subtotal}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-base-content/70">IGV (18%)</span>
              <span>S/ {igv}</span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-base-300">
              <span className="font-bold text-lg">Total</span>
              <span className="font-bold text-2xl text-primary">S/ {total}</span>
            </div>
          </div>

          <button 
            onClick={handleEmitir}
            disabled={cart.length === 0}
            className="btn btn-primary w-full btn-lg gap-2"
          >
            <Receipt size={24} /> Cobrar y Emitir
          </button>
        </div>
      </div>
    </div>
  );
};

// Pequeño workaround para usar el icono en este archivo sin importarlo arriba y chocar con lucide-react si no está
const ShoppingCartIcon = ({size, className}) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg>
);

export default POS;
