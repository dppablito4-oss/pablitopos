import React from 'react';
import { QRCodeSVG } from 'qrcode.react';

// === Convertir número a letras (español) ===
const UNIDADES = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE'];
const ESPECIALES = ['DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE'];
const DECENAS = ['', '', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA'];
const CENTENAS = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'];

const numToWords = (n) => {
  if (n === 0) return 'CERO';
  if (n === 100) return 'CIEN';
  const convertGroup = (num) => {
    if (num === 0) return '';
    if (num === 100) return 'CIEN';
    let result = '';
    if (num >= 100) { result += CENTENAS[Math.floor(num / 100)] + ' '; num %= 100; }
    if (num >= 10 && num <= 15) return result + ESPECIALES[num - 10];
    if (num >= 16 && num <= 19) return result + 'DIECI' + UNIDADES[num - 10];
    if (num >= 21 && num <= 29) return result + 'VEINTI' + UNIDADES[num - 20];
    if (num >= 10) { result += DECENAS[Math.floor(num / 10)]; num %= 10; if (num > 0) result += ' Y '; }
    result += UNIDADES[num];
    return result.trim();
  };
  let words = '';
  if (n >= 1000) {
    const miles = Math.floor(n / 1000);
    words += (miles === 1 ? 'MIL' : convertGroup(miles) + ' MIL') + ' ';
    n %= 1000;
  }
  words += convertGroup(n);
  return words.trim();
};

const montoEnLetras = (monto) => {
  const entero = Math.floor(monto);
  const decimales = Math.round((monto - entero) * 100);
  return `SON ${numToWords(entero)} CON ${String(decimales).padStart(2, '0')}/100 SOLES`;
};

// === Línea punteada reutilizable ===
const Dashed = () => <div style={{ borderBottom: '1px dashed #000', margin: '6px 0' }} />;

const PrintReceipt = ({ cart, totals, emisionType, printFormat, receiptData, regimeConfig, isPreview = false }) => {
  if (!receiptData) return null;

  const isTicket = printFormat === 'TICKET';
  const isBoleta = emisionType === 'Boleta Electrónica' || emisionType === 'Factura Electrónica';
  const legalText = regimeConfig?.legalText || 'Sujeto al Nuevo Régimen Único Simplificado - NRUS';
  const correlativo8 = String(receiptData.correlativo).padStart(8, '0');
  const fecha = new Date(receiptData.fechaEmision);
  const fechaStr = fecha.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  const horaStr = fecha.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const totalNum = parseFloat(totals.total);
  const fechaEmisionShort = receiptData.fechaEmision.split('T')[0];
  
  // Cadena oficial QR SUNAT: RUC | TIPO_DOC | SERIE | CORRELATIVO_8 | IGV | TOTAL | FECHA | TIPO_DOC_CLIENTE | NUM_DOC_CLIENTE | HASH
  const tipoDocCod = emisionType === 'Factura Electrónica' ? '01' : '03';
  const tipoDocCli = receiptData.cliente.numDoc.length === 11 ? '6' : (receiptData.cliente.numDoc.length === 8 ? '1' : '0');
  const qrValue = `${receiptData.company.ruc}|${tipoDocCod}|${receiptData.serie}|${correlativo8}|${totals.igv}|${totals.total}|${fechaEmisionShort}|${tipoDocCli}|${receiptData.cliente.numDoc}|${receiptData.hash || ''}`;

  // ====== TICKET 80mm ======
  if (isTicket) {
    return (
      <>
        {!isPreview && (
          <style>{`
            @media print {
              @page { size: 80mm auto; margin: 0; }
              body { margin: 0; }
            }
          `}</style>
        )}
        <div className={isPreview ? "mx-auto shadow-lg" : "hidden print:block absolute top-0 left-0 w-full bg-white text-black z-50"}
             style={isPreview ? { width: '302px', backgroundColor: '#ffffff', color: '#000000' } : {}}>
        <div style={{ maxWidth: '302px', margin: '0 auto', padding: '10px 8px', fontFamily: 'monospace', fontSize: '11px', lineHeight: '1.4' }}>
          
          {/* CABECERA EMISOR */}
          <div style={{ textAlign: 'center' }}>
            {receiptData.company.logo_base64 && (
              <img src={receiptData.company.logo_base64} alt="Logo" style={{ maxWidth: '140px', maxHeight: '60px', margin: '0 auto 8px', display: 'block', filter: 'grayscale(100%)' }} />
            )}
            <p style={{ fontSize: '16px', fontWeight: 'bold', margin: '0 0 2px' }}>{receiptData.company.razonSocial}</p>
            <p style={{ margin: '0' }}>RUC: {receiptData.company.ruc}</p>
            <p style={{ margin: '0', fontSize: '10px' }}>{receiptData.company.direccion}</p>
          </div>

          <Dashed />

          {/* TIPO DE DOCUMENTO */}
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontWeight: 'bold', margin: '0', fontSize: '12px' }}>{emisionType.toUpperCase()}</p>
            <p style={{ fontWeight: 'bold', margin: '0', fontSize: '13px' }}>{receiptData.serie} - {correlativo8}</p>
            <p style={{ margin: '0', fontSize: '10px' }}>Fecha de Emisión: {fechaStr} {horaStr}</p>
          </div>

          <Dashed />

          {/* DATOS DEL CLIENTE */}
          <div>
            <p style={{ margin: '0' }}><b>Cliente:</b> {receiptData.cliente.rznSocial}</p>
            <p style={{ margin: '0' }}><b>Documento:</b> {receiptData.cliente.numDoc}</p>
            <p style={{ margin: '0' }}><b>F. Pago:</b> {receiptData?.paymentMethod || 'Efectivo'}</p>
          </div>

          <Dashed />

          {/* TABLA DE PRODUCTOS */}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #000' }}>
                <th style={{ textAlign: 'left', padding: '2px 0', width: '28px' }}>Cant</th>
                <th style={{ textAlign: 'left', padding: '2px 0' }}>Descripción</th>
                <th style={{ textAlign: 'right', padding: '2px 0', width: '42px' }}>P.U.</th>
                <th style={{ textAlign: 'right', padding: '2px 0', width: '48px' }}>Total</th>
              </tr>
            </thead>
            <tbody>
              {cart.map((item, i) => (
                <tr key={i}>
                  <td style={{ padding: '2px 0', verticalAlign: 'top' }}>{item.quantity}</td>
                  <td style={{ padding: '2px 0', verticalAlign: 'top', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</td>
                  <td style={{ textAlign: 'right', padding: '2px 0', verticalAlign: 'top' }}>{item.price.toFixed(2)}</td>
                  <td style={{ textAlign: 'right', padding: '2px 0', verticalAlign: 'top' }}>{item.subtotal.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <Dashed />

          {/* TOTALES */}
          <div style={{ textAlign: 'right', fontSize: '11px' }}>
            {isBoleta && (
              <>
                <p style={{ margin: '0' }}>Subtotal: S/ {totals.subtotal}</p>
                <p style={{ margin: '0' }}>IGV (18%): S/ {totals.igv}</p>
              </>
            )}
            <p style={{ margin: '2px 0 0', fontWeight: 'bold', fontSize: '14px' }}>TOTAL: S/ {totals.total}</p>
          </div>

          <Dashed />

          {/* MONTO EN LETRAS */}
          <p style={{ margin: '0', fontSize: '9px', textAlign: 'center' }}>
            {montoEnLetras(totalNum)}
          </p>

          <Dashed />

          {/* QR + HASH */}
          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <QRCodeSVG value={qrValue} size={110} level="H" style={{ margin: '0 auto', width: '110px', height: '110px', display: 'block' }} />
            {receiptData.hash && (
              <p style={{ margin: '4px 0 0', fontSize: '8px', wordBreak: 'break-all' }}>
                Hash: {receiptData.hash}
              </p>
            )}
            {receiptData.sunatWarning && (
              <p style={{ margin: '2px 0', fontSize: '8px', fontStyle: 'italic' }}>⚠ Firma digital pendiente</p>
            )}
          </div>

          <Dashed />

          {/* PIE LEGAL */}
          <div style={{ textAlign: 'center', fontSize: '8px', lineHeight: '1.3' }}>
            <p style={{ margin: '0' }}>{legalText}</p>
            <p style={{ margin: '4px 0 0' }}>Representación impresa de la</p>
            <p style={{ margin: '0' }}>{isBoleta ? 'Boleta de Venta Electrónica' : emisionType}.</p>
            <p style={{ margin: '6px 0 0', fontWeight: 'bold' }}>¡Gracias por su compra!</p>
            <p style={{ margin: '2px 0 0' }}>Consulte su comprobante en:</p>
            <p style={{ margin: '0' }}>facturacion.sypablitodp.site/#/verificacion</p>
          </div>
        </div>
      </div>
      </>
    );
  }

  // ====== FORMATO A4 ======
  return (
    <>
      {!isPreview && (
        <style>{`
          @media print {
            @page { size: A4 portrait; margin: 10mm; }
          }
        `}</style>
      )}
      <div className={isPreview ? "mx-auto shadow-2xl" : "hidden print:block absolute top-0 left-0 w-full bg-white text-black z-50"}
           style={isPreview ? { width: '100%', maxWidth: '794px', minHeight: '1123px', backgroundColor: '#ffffff', color: '#000000' } : {}}>
      <div style={{ maxWidth: '700px', margin: '0 auto', padding: '40px 50px', fontFamily: "'Segoe UI', Arial, sans-serif", fontSize: '12px', lineHeight: '1.5' }}>
        
        {/* CABECERA A4 - Estilo comprobante formal */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          {/* Izquierda: Empresa */}
          <div style={{ flex: 1, display: 'flex', gap: '15px', alignItems: 'center' }}>
            {receiptData.company.logo_base64 && (
              <img src={receiptData.company.logo_base64} alt="Logo" style={{ maxWidth: '120px', maxHeight: '80px', objectFit: 'contain' }} />
            )}
            <div>
              <h1 style={{ fontSize: '22px', fontWeight: 'bold', margin: '0 0 4px' }}>{receiptData.company.razonSocial}</h1>
              <p style={{ margin: '0', fontSize: '11px', color: '#555' }}>{receiptData.company.direccion}</p>
            </div>
          </div>
          {/* Derecha: RUC y Tipo Doc */}
          <div style={{ border: '2px solid #1a56db', padding: '12px 20px', textAlign: 'center', minWidth: '220px' }}>
            <p style={{ margin: '0', fontWeight: 'bold', fontSize: '13px' }}>RUC: {receiptData.company.ruc}</p>
            <p style={{ margin: '6px 0', fontWeight: 'bold', fontSize: '11px', color: '#1a56db' }}>{emisionType.toUpperCase()}</p>
            <p style={{ margin: '0', fontWeight: 'bold', fontSize: '15px' }}>N° {receiptData.serie}-{correlativo8}</p>
          </div>
        </div>

        {/* INFO EMISIÓN Y CLIENTE */}
        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #ddd', borderBottom: '1px solid #ddd', padding: '10px 0', marginBottom: '16px', fontSize: '11px' }}>
          <div>
            <p style={{ margin: '0' }}><b>CLIENTE:</b> {receiptData.cliente.rznSocial}</p>
            <p style={{ margin: '0' }}><b>DNI/RUC:</b> {receiptData.cliente.numDoc}</p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ margin: '0' }}><b>FECHA:</b> {fechaStr}</p>
            <p style={{ margin: '0' }}><b>HORA:</b> {horaStr}</p>
            <p style={{ margin: '0' }}><b>MONEDA:</b> SOLES</p>
          </div>
        </div>

        {/* TABLA DE PRODUCTOS */}
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '16px', fontSize: '11px' }}>
          <thead>
            <tr style={{ borderTop: '2px solid #1a56db', borderBottom: '2px solid #1a56db', background: '#f0f4ff' }}>
              <th style={{ textAlign: 'center', padding: '6px 4px', width: '50px' }}>CANT</th>
              <th style={{ textAlign: 'left', padding: '6px 4px' }}>DESCRIPCIÓN</th>
              <th style={{ textAlign: 'right', padding: '6px 4px', width: '80px' }}>P.U.</th>
              <th style={{ textAlign: 'right', padding: '6px 4px', width: '90px' }}>IMPORTE</th>
            </tr>
          </thead>
          <tbody>
            {cart.map((item, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ textAlign: 'center', padding: '5px 4px' }}>{item.quantity}</td>
                <td style={{ padding: '5px 4px' }}>{item.name}</td>
                <td style={{ textAlign: 'right', padding: '5px 4px' }}>{item.price.toFixed(2)}</td>
                <td style={{ textAlign: 'right', padding: '5px 4px' }}>{item.subtotal.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* TOTALES */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
          <div style={{ width: '250px', fontSize: '11px' }}>
            {isBoleta && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
                  <span>SUBTOTAL ITEMS:</span><span>S/ {totals.subtotal}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
                  <span>IGV (18%):</span><span>S/ {totals.igv}</span>
                </div>
              </>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderTop: '2px solid #1a56db', fontWeight: 'bold', fontSize: '14px' }}>
              <span>IMPORTE TOTAL:</span><span>S/ {totals.total}</span>
            </div>
          </div>
        </div>

        {/* PIE: MONTO EN LETRAS + QR + LEGAL */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderTop: '1px solid #ddd', paddingTop: '12px' }}>
          <div style={{ fontSize: '10px', maxWidth: '380px' }}>
            <p style={{ margin: '0 0 4px', fontWeight: 'bold' }}>{montoEnLetras(totalNum)}</p>
            {receiptData.hash && (
              <p style={{ margin: '0 0 8px', fontSize: '9px', wordBreak: 'break-all', color: '#666' }}>
                Hash: {receiptData.hash}
              </p>
            )}
            <p style={{ margin: '0', color: '#555' }}>{legalText}</p>
            <p style={{ margin: '0', color: '#555' }}>Representación impresa de la {isBoleta ? 'Boleta de Venta Electrónica' : emisionType}.</p>
            <p style={{ margin: '4px 0 0', color: '#555' }}>Consulte su comprobante en: facturacion.sypablitodp.site/#/verificacion</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <QRCodeSVG value={qrValue} size={100} level="H" style={{ width: '100px', height: '100px', display: 'block', margin: '0 auto' }} />
            <p style={{ margin: '4px 0 0', fontSize: '8px', color: '#888' }}>Código Verificación</p>
          </div>
        </div>
      </div>
      </div>
    </>
  );
};

export default PrintReceipt;
