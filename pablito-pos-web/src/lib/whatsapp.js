export const getWhatsAppLink = (phone, cart, totals, emisionType) => {
  let text = `*NUEVA COMPRA* 🛒\n`;
  text += `Documento: ${emisionType}\n`;
  text += `------------------------\n`;
  
  cart.forEach(item => {
    text += `- ${item.quantity}x ${item.name} (S/ ${item.subtotal.toFixed(2)})\n`;
  });
  
  text += `------------------------\n`;
  text += `*Subtotal:* S/ ${totals.subtotal}\n`;
  if (emisionType === 'Boleta Electrónica') {
    text += `*IGV:* S/ ${totals.igv}\n`;
  }
  text += `*TOTAL:* S/ ${totals.total}\n\n`;
  text += `¡Gracias por tu compra en Pablito POS! ✨`;

  const encodedText = encodeURIComponent(text);
  
  // Si phone esta vacio, abre wa.me solo con el texto para elegir contacto
  const phoneParam = phone ? phone.replace(/\D/g, '') : '';
  return `https://wa.me/${phoneParam}?text=${encodedText}`;
};
