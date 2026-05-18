import { useState, useEffect } from 'react';
import { getMonthlyOfficialSalesTotal } from '../services/nrusService';

const NRUS_WARNING_LIMIT = 7500;
const NRUS_MAX_LIMIT = 8000;

export const useNrusValve = (currentCartTotal) => {
  const [monthlyTotal, setMonthlyTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTotal = async () => {
      setIsLoading(true);
      const total = await getMonthlyOfficialSalesTotal();
      setMonthlyTotal(total);
      setIsLoading(false);
    };
    
    fetchTotal();
  }, []);

  const totalProyectado = monthlyTotal + currentCartTotal;
  const isDangerZone = totalProyectado > NRUS_WARNING_LIMIT;
  const isExceeded = totalProyectado > NRUS_MAX_LIMIT;

  return {
    monthlyTotal,
    totalProyectado,
    isDangerZone,
    isExceeded,
    isLoading,
    limit: NRUS_MAX_LIMIT
  };
};
