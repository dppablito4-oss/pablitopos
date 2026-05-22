import React from 'react';
import { QRCodeSVG } from 'qrcode.react';

const PrintReceipt = ({ cart, totals, emisionType, printFormat, receiptData }) => {
  // Solo se renderiza si hay datos de recibo (cuando ya se dio "Cobrar")
  if (!receiptData) return null;

  const isTicket = printFormat === 'TICKET';
  
  // Format classes based on selection
  const containerClass = isTicket 
    ? "print-ticket font-mono text-sm" 
    : "print-a4 font-sans text-base";

  return (
    <div className="hidden print:block absolute top-0 left-0 w-full bg-white text-black z-50">
      <div className={`${containerClass} mx-auto p-4`}>
        
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="font-bold text-2xl uppercase">{receiptData.company.razonSocial}</h1>
          <p>RUC: {receiptData.company.ruc}</p>
          <p className="text-sm">{receiptData.company.direccion}</p>
          <p className="mt-2 font-bold uppercase">{emisionType}</p>
          <p>{receiptData.serie}-{receiptData.correlativo}</p>
          <p className="text-sm mt-1">{new Date(receiptData.fechaEmision).toLocaleString()}</p>
        </div>

        {/* Client Info (More prominent in A4) */}
        {!isTicket && (
          <div className="mb-6 border-t border-b border-black py-2">
            <p><strong>Cliente:</strong> {receiptData.cliente.rznSocial}</p>
            <p><strong>Doc:</strong> {receiptData.cliente.numDoc}</p>
          </div>
        )}

        {/* Items Table */}
        <table className="w-full text-left mb-6 border-collapse">
          <thead>
            <tr className="border-b border-black">
              <th className="py-1">Cant</th>
              <th className="py-1">Descripción</th>
              <th className="py-1 text-right">P.U</th>
              <th className="py-1 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {cart.map((item, i) => (
              <tr key={i} className="border-b border-gray-300">
                <td className="py-2">{item.quantity}</td>
                <td className="py-2">{item.name}</td>
                <td className="py-2 text-right">{item.price.toFixed(2)}</td>
                <td className="py-2 text-right">{item.subtotal.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Totals */}
        <div className="flex flex-col items-end mb-8 space-y-1">
          <div className="w-48 flex justify-between">
            <span>Subtotal:</span>
            <span>S/ {totals.subtotal}</span>
          </div>
          {emisionType === 'Boleta Electrónica' && (
            <div className="w-48 flex justify-between">
              <span>IGV (18%):</span>
              <span>S/ {totals.igv}</span>
            </div>
          )}
          <div className="w-48 flex justify-between font-bold text-lg pt-2 border-t border-black">
            <span>TOTAL:</span>
            <span>S/ {totals.total}</span>
          </div>
        </div>

        {/* Footer & QR */}
        <div className="text-center flex flex-col items-center">
          {receiptData.hash && (
            <div className="mb-4 flex flex-col items-center">
              <QRCodeSVG value={`${receiptData.company.ruc}|03|${receiptData.serie}|${receiptData.correlativo}|${totals.igv}|${totals.total}|${receiptData.fechaEmision.split('T')[0]}|1|${receiptData.cliente.numDoc}|${receiptData.hash}`} size={isTicket ? 120 : 150} />
              <p className="text-xs mt-2 break-all w-full max-w-xs font-mono">{receiptData.hash}</p>
            </div>
          )}
          {receiptData.sunatWarning && (
            <p className="text-xs italic mb-2">⚠️ Firma digital pendiente</p>
          )}
          <p className="font-bold">¡Gracias por su compra!</p>
          <p className="text-xs">Representación impresa generada por Pablito POS Web</p>
        </div>

      </div>
    </div>
  );
};

export default PrintReceipt;
