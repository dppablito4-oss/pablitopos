/**
 * Servicio para conectar con la API en PHP alojada en Render (Imagen Docker: giansmar/lycet)
 */

const SUNAT_API_URL = import.meta.env.VITE_SUNAT_API_URL || 'https://tu-api-render.onrender.com';

export const generarHashSunat = async (saleData, items) => {
  try {
    // Aquí debemos formatear los datos de la venta al formato JSON que espera la API PHP (Lycet)
    // Este formato dependerá de la documentación exacta de giansmar/lycet
    const payload = {
      tipoDoc: "03", // Boleta
      serie: saleData.series,
      correlativo: saleData.number.toString(),
      fechaEmision: new Date().toISOString(),
      cliente: {
        tipoDoc: "1", // DNI
        numDoc: "00000000",
        rznSocial: "CLIENTE VARIOS"
      },
      company: {
        ruc: "20123456789",
        razonSocial: "PABLITO POS"
      },
      mtoOperGravadas: saleData.subtotal,
      mtoIGV: saleData.igv,
      totalImpuestos: saleData.igv,
      valorVenta: saleData.subtotal,
      mtoImpVenta: saleData.total,
      details: items.map(item => ({
        codProducto: item.product_id.toString(),
        unidad: "NIU",
        descripcion: item.description,
        cantidad: item.quantity,
        mtoValorUnitario: item.unit_price,
        mtoValorVenta: item.subtotal,
        mtoBaseIgv: item.subtotal,
        porcentajeIgv: 18,
        igv: item.subtotal * 0.18,
        tipAfeIgv: 10,
        totalImpuestos: item.subtotal * 0.18,
        mtoPrecioUnitario: item.unit_price * 1.18
      }))
    };

    console.log("Enviando a SUNAT API (Render):", payload);

    /* Descomentar cuando la API esté en Render:
    const response = await fetch(`${SUNAT_API_URL}/api/v1/invoice/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error("Error en la respuesta de SUNAT API");
    }

    const result = await response.json();
    return result.hash; // O el campo exacto que devuelva Lycet
    */

    // MOCK para pruebas:
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve("mock_hash_sunat_12345xyz");
      }, 1000);
    });

  } catch (error) {
    console.error("Error al comunicarse con Render/SUNAT:", error);
    throw error;
  }
};
