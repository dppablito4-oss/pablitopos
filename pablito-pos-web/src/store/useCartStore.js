import { create } from 'zustand';

const IGV_RATE = 0.18;

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

export const useCartStore = create((set, get) => ({
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
    const { cart } = get();
    const subtotal = cart.reduce((sum, item) => sum + item.subtotal, 0);
    const igv = subtotal * IGV_RATE;
    const total = subtotal + igv;
    
    return {
      subtotal: subtotal.toFixed(2),
      igv: igv.toFixed(2),
      total: total.toFixed(2),
      itemCount: cart.reduce((count, item) => count + item.quantity, 0)
    };
  }
}));
