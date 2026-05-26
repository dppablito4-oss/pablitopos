-- ========================================================
-- SCRIPT: CORRELATIVOS MULTI-TENANT PARA SAAS (FASE 2)
-- ========================================================

-- 1. Modificar tabla document_sequences para incluir company_id
ALTER TABLE public.document_sequences DROP CONSTRAINT IF EXISTS document_sequences_pkey;
ALTER TABLE public.document_sequences ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id);

-- Asignar las secuencias existentes a la primera empresa (Grafiplot)
UPDATE public.document_sequences SET company_id = 1 WHERE company_id IS NULL;
ALTER TABLE public.document_sequences ALTER COLUMN company_id SET NOT NULL;

-- Recrear llave primaria compuesta para que la combinación (company_id, series) sea única
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'document_sequences_pkey' 
        AND conrelid = 'public.document_sequences'::regclass
    ) THEN
        ALTER TABLE public.document_sequences ADD PRIMARY KEY (company_id, series);
    END IF;
END $$;

-- 2. Habilitar RLS en document_sequences
ALTER TABLE public.document_sequences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "auth_manage_own_sequences" ON public.document_sequences;
CREATE POLICY "auth_manage_own_sequences" ON public.document_sequences FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));

-- 3. Actualizar función assign_sale_correlative para manejar company_id dinámico
CREATE OR REPLACE FUNCTION assign_sale_correlative()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_company_id BIGINT;
BEGIN
    -- Obtener el company_id (si no viene en la inserción, lo extraemos del perfil del usuario activo)
    IF NEW.company_id IS NULL OR NEW.company_id = 1 THEN
        v_company_id := (SELECT company_id FROM public.profiles WHERE id = auth.uid());
        -- Si no hay usuario logueado (ej. pruebas directas), usar el por defecto (1)
        IF v_company_id IS NULL THEN
            v_company_id := 1;
        END IF;
        NEW.company_id := v_company_id;
    ELSE
        v_company_id := NEW.company_id;
    END IF;

    -- Asignar el número de boleta/factura solo si no viene uno manual
    IF NEW.number IS NULL OR NEW.number = 0 THEN
        INSERT INTO public.document_sequences (company_id, series, current_number)
        VALUES (v_company_id, NEW.series, 1)
        ON CONFLICT (company_id, series) DO UPDATE
        SET current_number = document_sequences.current_number + 1
        RETURNING current_number INTO NEW.number;
    END IF;
    RETURN NEW;
END;
$$;
