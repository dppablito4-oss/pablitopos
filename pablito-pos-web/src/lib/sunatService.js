import { supabase } from './supabase';

const SUNAT_API_URL = import.meta.env.VITE_SUNAT_API_URL || 'https://pablitopos.onrender.com';

// Ping para despertar el servidor Render
export const pingSunatApi = async () => {
  try {
    fetch(`${SUNAT_API_URL}/ping`, { method: 'GET', mode: 'no-cors' }).catch(() => {});
  } catch (e) {
    // Ignoramos errores, es solo un ping
  }
};

export const generarHashSunat = async (saleData, items) => {
  // 1. Obtener la configuración activa de la empresa
  const { data: company } = await supabase
    .from('company_profile')
    .select('*')
    .eq('is_active', true)
    .limit(1)
    .single();

  if (!company) {
    throw new Error("No se encontró el perfil de empresa en Configuración.");
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
    price: parseFloat(item.unit_price || 0),
    description: item.description || 'PRODUCTO'
  }));

  // 4. Formatear leyenda
  const leyenda = `SON ${parseFloat(saleData.total).toFixed(2)} SOLES`;

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
    // NOTA DE SEGURIDAD: Ya no enviamos sol_user, sol_pass ni cert_pem desde aquí.
    // El backend los obtendrá directamente de forma segura.
    production: company.production || false
  };

  // Obtener Token de Autenticación del usuario logueado
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token || '';

  console.log("📡 Enviando a SUNAT API:", SUNAT_API_URL);

  // Fetch con timeout de 30 segundos (Render puede hacer cold-start)
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(`${SUNAT_API_URL}/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    const result = await response.json();
    console.log("📬 Respuesta SUNAT API:", result);

    if (!result.success) {
      throw new Error(result.error || "SUNAT rechazó el documento.");
    }

    // Retorna el hash y los archivos codificados
    return {
      hash: result.hash || null,
      xml_base64: result.xml_base64 || null,
      cdr_base64: result.cdr_base64 || null
    };

  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error("Timeout: El servidor de facturación no respondió a tiempo. La venta se guardó sin firma digital.");
    }
    throw err;
  }
};
