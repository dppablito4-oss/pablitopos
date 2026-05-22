import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const EMISION_TYPES = {
  BOLETA: 'Boleta Electrónica',
  NOTA: 'Nota de Venta Interna',
  ADELANTO: 'Adelanto',
  COTIZACION: 'Cotización'
};

export const PRINT_FORMATS = {
  TICKET: 'TICKET',
  A4: 'A4'
};

export const useCartStore = create(persist((set, get) => ({
  cart: [],
  emisionType: EMISION_TYPES.BOLETA,
  printFormat: PRINT_FORMATS.TICKET,
  lastReceipt: null, // Guardaremos los datos de la última venta para impresión
  
  setEmisionType: (type) => set({ emisionType: type }),
  setPrintFormat: (format) => set({ printFormat: format }),
  setLastReceipt: (receiptData) => set({ lastReceipt: receiptData }),

  addItem: (product) => set((state) => {
    const existingItem = state.cart.find(item => item.id === product.id);
    if (existingItem) {
      return {
        cart: state.cart.map(item => 
          item.id === product.id 
            ? { ...item, quantity: item.quantity + 1, subtotal: (item.quantity + 1) * item.price } 
            : item
        )
      };
    }
    return {
      cart: [...state.cart, { ...product, quantity: 1, subtotal: product.price }]
    };
  }),

  removeItem: (productId) => set((state) => ({
    cart: state.cart.filter(item => item.id !== productId)
  })),

  updateQuantity: (productId, quantity) => set((state) => ({
    cart: state.cart.map(item => 
      item.id === productId 
        ? { ...item, quantity: Math.max(1, quantity), subtotal: Math.max(1, quantity) * item.price }
        : item
    )
  })),

  clearCart: () => set({ cart: [], emisionType: EMISION_TYPES.BOLETA }),

  getTotals: () => {
    const { cart, emisionType } = get();
    const sumaPrecio = cart.reduce((sum, item) => sum + item.subtotal, 0);
    const isBoleta = emisionType === EMISION_TYPES.BOLETA;
    
    // Los precios YA incluyen IGV.
    // Para Boleta: descomponemos en base imponible + IGV
    // Para otros tipos: no aplica IGV
    const total = sumaPrecio;
    const baseImponible = isBoleta ? parseFloat((sumaPrecio / 1.18).toFixed(2)) : sumaPrecio;
    const igv = isBoleta ? parseFloat((sumaPrecio - baseImponible).toFixed(2)) : 0;

    return {
      subtotal: baseImponible.toFixed(2),
      igv: igv.toFixed(2),
      total: total.toFixed(2),
      itemCount: cart.reduce((count, item) => count + item.quantity, 0)
    };
  }
}), {
  name: 'pablito-cart',
  partialize: (state) => ({ cart: state.cart, emisionType: state.emisionType, printFormat: state.printFormat }),
}));
