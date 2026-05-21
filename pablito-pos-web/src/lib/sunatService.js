import { supabase } from './supabase';

const SUNAT_API_URL = import.meta.env.VITE_SUNAT_API_URL || 'https://pablitopos.onrender.com';

export const generarHashSunat = async (saleData, items) => {
  try {
    // 1. Obtener la configuración activa de la empresa
    const { data: company } = await supabase
      .from('company_profile')
      .select('*')
      .eq('is_active', true)
      .limit(1)
      .single();

    if (!company) {
      throw new Error("No se encontró la configuración del perfil de la empresa.");
    }

    // 2. Determinar tipo de documento del cliente
    let clienteDoc = '00000000';
    let clienteNombre = 'CLIENTE VARIOS';
    let clienteTipoDoc = '1';

    if (saleData.client_id) {
      const { data: client } = await supabase
        .from('clients')
        .select('*')
        .eq('id', saleData.client_id)
        .single();
      if (client) {
        clienteDoc = client.dni || '00000000';
        clienteNombre = client.full_name || 'CLIENTE VARIOS';
        clienteTipoDoc = clienteDoc.length === 11 ? '6' : '1';
      }
    }

    // 3. Convertir items del formato de base de datos a formato API
    const itemsFormatted = items.map(item => ({
      code: item.product_id?.toString() || 'P001',
      name: item.description || 'PRODUCTO',
      unit: item.unit || 'NIU',
      quantity: parseFloat(item.quantity || 1),
      price: parseFloat(item.unit_price || 0), // El precio con IGV
      description: item.description || 'PRODUCTO'
    }));

    // 4. Formatear leyenda
    const leyenda = `SON ${saleData.total.toFixed(2)} SOLES`;

    const payload = {
      ruc: company.ruc || '20000000001',
      razonSocial: company.name || 'EMPRESA DE PRUEBA',
      direccion: company.address || 'AV PRINCIPAL S/N',
      serie: saleData.series,
      correlativo: saleData.number.toString(),
      clienteDoc,
      clienteNombre,
      clienteTipoDoc,
      subtotal: parseFloat(saleData.subtotal || 0),
      igv: parseFloat(saleData.igv || 0),
      total: parseFloat(saleData.total || 0),
      leyenda,
      items: itemsFormatted,
      sol_user: company.sol_user,
      sol_pass: company.sol_pass,
      cert_pem: company.cert_pem,
      production: company.production || false
    };

    console.log("Enviando a SUNAT API (Render):", payload);

    const response = await fetch(`${SUNAT_API_URL}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();
    console.log("Respuesta de SUNAT API:", result);

    if (!result.success) {
      throw new Error(result.error || "Error desconocido al procesar con SUNAT");
    }

    return result.hash; // Retorna el hash real (DigestValue) de la firma

  } catch (error) {
    console.error("Error al comunicarse con Render/SUNAT:", error);
    throw error;
  }
};
