import { supabase } from '../lib/supabase';

/**
 * Consulta a Supabase el total de ventas mensuales oficiales (Boletas).
 * Asumimos que las boletas se identifican porque su 'series' empieza con 'B'.
 */
export const getMonthlyOfficialSalesTotal = async () => {
  const now = new Date();
  // Primer dia del mes actual (hora local a UTC aprox para la busqueda)
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
  
  try {
    const { data, error } = await supabase
      .from('sales')
      .select('total')
      .gte('datetime', firstDay)
      .like('series', 'B%');

    if (error) {
      console.error("Error fetching monthly sales for NRUS:", error);
      return 0;
    }

    const totalAcumulado = data.reduce((sum, sale) => sum + (sale.total || 0), 0);
    return totalAcumulado;
  } catch (err) {
    console.error("Unexpected error in NRUS service:", err);
    return 0;
  }
};
