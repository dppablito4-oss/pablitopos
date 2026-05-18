import jsPDF from 'jspdf';
import 'jspdf-autotable';

export const generateTicketPDF = (cartData, totals, companyData = null, hashSunat = null) => {
  // Configuración de un formato ticket térmico aproximado (80mm)
  // 80mm de ancho x altura dinámica
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: [80, 200] // Altura ajustable luego si es necesario
  });

  const margins = { top: 10, left: 5, right: 5 };
  let y = margins.top;

  // Company Header
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.text(companyData?.name || "PABLITO POS", 40, y, { align: "center" });
  y += 5;
  
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text(`RUC: ${companyData?.ruc || '10123456789'}`, 40, y, { align: "center" });
  y += 4;
  doc.text(`Telf: ${companyData?.phone || '999-999-999'}`, 40, y, { align: "center" });
  y += 8;

  // Title
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("BOLETA DE VENTA ELECTRÓNICA", 40, y, { align: "center" });
  y += 5;
  doc.text("B001-0000001", 40, y, { align: "center" }); // Mock número
  y += 8;

  // Date
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text(`Fecha: ${new Date().toLocaleString()}`, margins.left, y);
  y += 6;

  // Table
  const tableColumn = ["Cant", "Descripción", "P.U", "Total"];
  const tableRows = cartData.map(item => [
    item.quantity.toString(),
    item.name.substring(0, 15), // Truncate long names for ticket
    item.price.toFixed(2),
    item.subtotal.toFixed(2)
  ]);

  doc.autoTable({
    startY: y,
    head: [tableColumn],
    body: tableRows,
    theme: 'plain',
    styles: { fontSize: 8, cellPadding: 1, overflow: 'linebreak' },
    headStyles: { fontStyle: 'bold', borderBottom: '1px solid black' },
    margin: { left: 5, right: 5 },
    columnStyles: {
      0: { cellWidth: 8 },
      1: { cellWidth: 35 },
      2: { cellWidth: 12, halign: 'right' },
      3: { cellWidth: 15, halign: 'right' }
    }
  });

  y = doc.lastAutoTable.finalY + 5;

  // Totals
  doc.setFontSize(9);
  doc.text("Subtotal:", 40, y);
  doc.text(`S/ ${totals.subtotal}`, 75, y, { align: "right" });
  y += 4;
  doc.text("IGV (18%):", 40, y);
  doc.text(`S/ ${totals.igv}`, 75, y, { align: "right" });
  y += 4;
  
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("TOTAL:", 40, y);
  doc.text(`S/ ${totals.total}`, 75, y, { align: "right" });
  y += 10;

  // Footer
  doc.setFontSize(8);
  doc.setFont("helvetica", "normal");
  if (hashSunat) {
    doc.text(`Hash SUNAT: ${hashSunat}`, 40, y, { align: "center" });
    y += 5;
  }
  doc.text("¡Gracias por su compra!", 40, y, { align: "center" });
  y += 4;
  doc.text("Generado por Pablito POS Web", 40, y, { align: "center" });

  // Open PDF in new tab
  doc.output('dataurlnewwindow');
};
