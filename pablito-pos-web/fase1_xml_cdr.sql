-- ==========================================
-- SCRIPT FASE 1: SOPORTE PARA DESCARGA DE XML Y CDR
-- ==========================================

-- 1. Agregamos las columnas para guardar los archivos brutos de SUNAT en base64
ALTER TABLE sales 
ADD COLUMN IF NOT EXISTS xml_base64 TEXT,
ADD COLUMN IF NOT EXISTS cdr_base64 TEXT;
