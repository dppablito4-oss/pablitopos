-- ==========================================
-- SCRIPT FASE 2: LOGOS Y PREPARATIVOS RLS
-- ==========================================

-- 1. Agregar soporte para Logo en Base64 en la tabla de empresas
ALTER TABLE company_profile 
ADD COLUMN IF NOT EXISTS logo_base64 TEXT;

-- (El código de RLS y separación de empresas por tenant
-- se implementará más adelante cuando tengas a tu segundo cliente real).
