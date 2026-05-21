-- ==========================================
-- POLÍTICAS RLS CON AUTENTICACIÓN
-- ==========================================
-- Solo usuarios autenticados via Supabase Auth 
-- pueden leer y escribir en las tablas.
-- Esto bloquea 100% a cualquier persona sin login.

-- 1. Activar RLS en todas las tablas
ALTER TABLE company_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiados ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiado_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- 2. Crear políticas: solo usuarios logueados pueden hacer todo
DO $$
DECLARE
  t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'company_profile','clients','products','sales',
    'sale_items','fiados','fiado_items','audit_logs','settings'
  ])
  LOOP
    -- Limpiar políticas antiguas
    EXECUTE format('DROP POLICY IF EXISTS "allow_all_select" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "allow_all_insert" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "allow_all_update" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "allow_all_delete" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_select" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_insert" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_update" ON %I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_delete" ON %I', t);
    
    -- Nuevas políticas: solo auth.uid() != null (usuario logueado)
    EXECUTE format('CREATE POLICY "auth_select" ON %I FOR SELECT TO authenticated USING (true)', t);
    EXECUTE format('CREATE POLICY "auth_insert" ON %I FOR INSERT TO authenticated WITH CHECK (true)', t);
    EXECUTE format('CREATE POLICY "auth_update" ON %I FOR UPDATE TO authenticated USING (true) WITH CHECK (true)', t);
    EXECUTE format('CREATE POLICY "auth_delete" ON %I FOR DELETE TO authenticated USING (true)', t);
  END LOOP;
END $$;
--

