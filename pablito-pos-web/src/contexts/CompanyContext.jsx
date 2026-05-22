import { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

export const TAX_REGIMES = {
  NRUS: 'nrus',
  RER: 'rer',
  MYPE: 'mype',
  GENERAL: 'general',
};

export const REGIME_CONFIG = {
  nrus: {
    name: 'Nuevo RUS (NRUS)',
    hasIgv: false,
    canEmitFactura: false,
    monthlyLimit: 8000,
    legalText: 'Sujeto al Nuevo Régimen Único Simplificado - NRUS',
  },
  rer: {
    name: 'Régimen Especial (RER)',
    hasIgv: true,
    canEmitFactura: true,
    monthlyLimit: null,
    legalText: 'Régimen Especial de Renta',
  },
  mype: {
    name: 'Mype Tributario',
    hasIgv: true,
    canEmitFactura: true,
    monthlyLimit: null,
    legalText: 'Régimen Mype Tributario',
  },
  general: {
    name: 'Régimen General',
    hasIgv: true,
    canEmitFactura: true,
    monthlyLimit: null,
    legalText: 'Régimen General',
  },
};

const CompanyContext = createContext(null);

export const CompanyProvider = ({ children }) => {
  const [company, setCompany] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchCompany = async () => {
    try {
      const { data } = await supabase
        .from('company_profile')
        .select('*')
        .eq('is_active', true)
        .limit(1)
        .single();
      if (data) setCompany(data);
    } catch (e) {
      console.error('Error loading company:', e);
    }
    setLoading(false);
  };

  useEffect(() => { fetchCompany(); }, []);

  const regime = company?.tax_regime || 'nrus';
  const regimeConfig = REGIME_CONFIG[regime] || REGIME_CONFIG.nrus;

  return (
    <CompanyContext.Provider value={{ company, loading, regime, regimeConfig, refetchCompany: fetchCompany }}>
      {children}
    </CompanyContext.Provider>
  );
};

export const useCompany = () => {
  const ctx = useContext(CompanyContext);
  if (!ctx) throw new Error('useCompany debe usarse dentro de CompanyProvider');
  return ctx;
};
