import React, { useState, useEffect } from 'react';
import { DollarSign, FileText, TrendingUp, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useCompany } from '../contexts/CompanyContext';

const Dashboard = () => {
  const [stats, setStats] = useState({
    ventasHoy: 0, ventasAyer: 0,
    boletasHoy: 0, boletasAyer: 0,
    fiadosPendientes: 0,
    topProductos: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [hora, setHora] = useState(new Date());
  const { company, regimeConfig } = useCompany();

  // Reloj en vivo
  useEffect(() => {
    const timer = setInterval(() => setHora(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (company) {
      fetchStats();
      const interval = setInterval(() => fetchStats(true), 30000); // auto-refresh 30s
      return () => clearInterval(interval);
    }
  }, [company]);

  const fetchStats = async (isAutoRefresh = false) => {
    if (isAutoRefresh) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);
    try {
      const hoyStart = new Date(); hoyStart.setHours(0,0,0,0);
      const hoyEnd = new Date(); hoyEnd.setHours(23,59,59,999);
      const ayerStart = new Date(hoyStart); ayerStart.setDate(ayerStart.getDate() - 1);
      const ayerEnd = new Date(hoyEnd); ayerEnd.setDate(ayerEnd.getDate() - 1);

      const [resHoy, resAyer, resFiados, resSaleItems] = await Promise.all([
        supabase.from('sales').select('id, total, is_proforma')
          .gte('datetime', hoyStart.toISOString())
          .lte('datetime', hoyEnd.toISOString()),
        supabase.from('sales').select('total, is_proforma')
          .gte('datetime', ayerStart.toISOString())
          .lte('datetime', ayerEnd.toISOString()),
        supabase.from('fiados').select('total_pendiente').eq('status', 'pendiente'),
        supabase.from('sale_items').select('description, quantity, subtotal, sale_id')
          .order('id', { ascending: false }).limit(500),
      ]);

      const ventasHoy = (resHoy.data || []).filter(v => !v.is_proforma).reduce((s, v) => s + parseFloat(v.total||0), 0);
      const ventasAyer = (resAyer.data || []).filter(v => !v.is_proforma).reduce((s, v) => s + parseFloat(v.total||0), 0);
      const boletasHoy = (resHoy.data || []).filter(v => !v.is_proforma).length;
      const boletasAyer = (resAyer.data || []).filter(v => !v.is_proforma).length;
      const fiadosPendientes = (resFiados.data || []).reduce((s, f) => s + parseFloat(f.total_pendiente||0), 0);

      // Top productos del día: filtrar items que pertenezcan a ventas de hoy
      // (sale_items no tiene created_at, así que usamos los sale_ids de hoy)
      const saleIdsHoy = new Set((resHoy.data || []).map(v => v.id).filter(Boolean));
      const todayItems = (resSaleItems.data || []).filter(i => saleIdsHoy.has(i.sale_id));
      const prodMap = {};
      todayItems.forEach(i => {
        prodMap[i.description] = (prodMap[i.description] || 0) + parseFloat(i.subtotal||0);
      });
      const topProductos = Object.entries(prodMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([name, total]) => ({ name, total }));

      setStats({ ventasHoy, ventasAyer, boletasHoy, boletasAyer, fiadosPendientes, topProductos });
    } catch (e) {
      setError('Error al cargar estadísticas: ' + e.message);
    }
    setIsLoading(false);
    setIsRefreshing(false);
  };

  const pctChange = (hoy, ayer) => {
    if (ayer === 0) return hoy > 0 ? 100 : 0;
    return (((hoy - ayer) / ayer) * 100).toFixed(1);
  };
  const ventasPct = pctChange(stats.ventasHoy, stats.ventasAyer);
  const boletasPct = pctChange(stats.boletasHoy, stats.boletasAyer);
  const ticketPromedio = stats.boletasHoy > 0 ? (stats.ventasHoy / stats.boletasHoy) : 0;

  // Límite mensual (según régimen activo)
  const monthlyLimit = regimeConfig?.monthlyLimit || null;
  const [ventasMes, setVentasMes] = useState(0);
  useEffect(() => {
    if (!company) return;
    const fetchMes = async () => {
      try {
        const mesStart = new Date(); mesStart.setDate(1); mesStart.setHours(0,0,0,0);
        const { data, error } = await supabase.from('sales').select('total').gte('datetime', mesStart.toISOString()).eq('is_proforma', false);
        if (error) {
          console.error("Supabase monthly sales query error:", error);
          return;
        }
        const total = (data||[]).reduce((s,v) => s + parseFloat(v.total||0), 0);
        setVentasMes(total);
      } catch (err) {
        console.error("Exception fetching monthly sales:", err);
      }
    };
    fetchMes();
  }, [stats, company]);

  const nrusPct = monthlyLimit ? Math.min(100, (ventasMes / monthlyLimit) * 100) : 0;
  const nrusColor = nrusPct >= 90 ? 'progress-error' : nrusPct >= 70 ? 'progress-warning' : 'progress-success';

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header con reloj */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-2">
        <div>
          <h2 className="text-xl md:text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-base-content/60 text-xs md:text-sm mt-0.5">
            {hora.toLocaleDateString('es-PE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <p className="text-lg md:text-2xl font-bold font-mono tabular-nums">
            {hora.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </p>
          <button className="btn btn-ghost btn-sm" onClick={() => fetchStats(true)} disabled={isLoading || isRefreshing}>
            <RefreshCw size={16} className={(isLoading || isRefreshing) ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {error && <div className="alert alert-warning shadow-sm text-sm"><AlertCircle size={16}/>{error}</div>}

      {/* KPI Cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <div className="bg-base-200 rounded-xl">
          <div className="p-3 md:p-5">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-base-content/60">Ventas de Hoy</p>
                <h3 className="text-lg md:text-2xl font-bold mt-0.5">
                  {isLoading ? <span className="loading loading-dots loading-sm"/> : `S/ ${stats.ventasHoy.toFixed(2)}`}
                </h3>
              </div>
              <div className="p-1.5 md:p-2 bg-success/10 text-success rounded-lg"><DollarSign size={18}/></div>
            </div>
            <p className={`text-xs mt-2 font-semibold ${parseFloat(ventasPct) >= 0 ? 'text-success' : 'text-error'}`}>
              {parseFloat(ventasPct) >= 0 ? '↑' : '↓'} {Math.abs(ventasPct)}% vs ayer
            </p>
          </div>
        </div>

        <div className="bg-base-200 rounded-xl">
          <div className="p-3 md:p-5">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-base-content/60">Comprobantes Hoy</p>
                <h3 className="text-lg md:text-2xl font-bold mt-0.5">
                  {isLoading ? <span className="loading loading-dots loading-sm"/> : stats.boletasHoy}
                </h3>
              </div>
              <div className="p-1.5 md:p-2 bg-primary/10 text-primary rounded-lg"><FileText size={18}/></div>
            </div>
            <p className={`text-xs mt-2 font-semibold ${parseFloat(boletasPct) >= 0 ? 'text-success' : 'text-error'}`}>
              {parseFloat(boletasPct) >= 0 ? '↑' : '↓'} {Math.abs(boletasPct)}% vs ayer
            </p>
          </div>
        </div>

        <div className="bg-base-200 rounded-xl">
          <div className="p-3 md:p-5">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-base-content/60">Ticket Promedio</p>
                <h3 className="text-lg md:text-2xl font-bold mt-0.5">
                  {isLoading ? <span className="loading loading-dots loading-sm"/> : `S/ ${ticketPromedio.toFixed(2)}`}
                </h3>
              </div>
              <div className="p-1.5 md:p-2 bg-info/10 text-info rounded-lg"><TrendingUp size={18}/></div>
            </div>
            <p className="text-xs mt-2 text-base-content/50">Promedio por comprobante</p>
          </div>
        </div>

        <div className="bg-base-200 rounded-xl">
          <div className="p-3 md:p-5">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs text-base-content/60">Fiados Pendientes</p>
                <h3 className="text-lg md:text-2xl font-bold mt-0.5 text-error">
                  {isLoading ? <span className="loading loading-dots loading-sm"/> : `S/ ${stats.fiadosPendientes.toFixed(2)}`}
                </h3>
              </div>
              <div className="p-1.5 md:p-2 bg-error/10 text-error rounded-lg"><Clock size={18}/></div>
            </div>
            <p className="text-xs mt-2 text-base-content/50">Total por cobrar</p>
          </div>
        </div>
      </div>

      {/* Limite Mensual + Top Productos */}
      <div className={`grid gap-3 ${monthlyLimit ? 'md:grid-cols-2' : 'md:grid-cols-1'}`}>
        {/* Gauge mensual — solo si el régimen tiene límite */}
        {monthlyLimit && (
        <div className="bg-base-200 rounded-xl">
          <div className="p-4">
            <h3 className="font-bold text-lg">Control {regimeConfig.name} Mensual</h3>
            <p className="text-base-content/60 text-sm mb-3">Límite: S/ {monthlyLimit.toLocaleString()}</p>
            <div className="flex justify-between text-sm mb-2">
              <span className="font-semibold">S/ {ventasMes.toFixed(2)}</span>
              <span className="text-base-content/50">{nrusPct.toFixed(1)}%</span>
            </div>
            <progress className={`progress ${nrusColor} w-full h-4`} value={nrusPct} max="100"></progress>
            {nrusPct >= 90 && (
              <div className="alert alert-error alert-sm mt-3 text-xs p-2">
                <AlertCircle size={14}/> ¡Atención! Muy cerca del límite {regimeConfig.name}.
              </div>
            )}
            {nrusPct >= 70 && nrusPct < 90 && (
              <div className="alert alert-warning alert-sm mt-3 text-xs p-2">
                <AlertCircle size={14}/> Acercándose al límite del mes.
              </div>
            )}
          </div>
        </div>
        )}

        {/* Top Productos */}
        <div className="bg-base-200 rounded-xl">
          <div className="p-4">
            <h3 className="font-bold text-lg">Top Productos Recientes</h3>
            <p className="text-base-content/60 text-sm mb-3">Por monto vendido</p>
            {isLoading ? (
              <div className="flex justify-center py-4"><span className="loading loading-spinner text-primary"/></div>
            ) : stats.topProductos.length === 0 ? (
              <p className="text-base-content/40 text-sm text-center py-4">Sin datos aún.</p>
            ) : (
              <div className="space-y-2">
                {stats.topProductos.map((p, i) => {
                  const maxTotal = stats.topProductos[0]?.total || 1;
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-base-content/50 w-4">#{i+1}</span>
                      <div className="flex-1">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium truncate max-w-[160px]">{p.name}</span>
                          <span className="text-primary font-bold">S/ {p.total.toFixed(2)}</span>
                        </div>
                        <progress className="progress progress-primary w-full h-1.5" value={p.total} max={maxTotal}></progress>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
