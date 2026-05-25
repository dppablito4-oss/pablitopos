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

-- ==========================================
-- POLÍTICAS ANON PARA VERIFICACIÓN PÚBLICA
-- ==========================================
-- La página de verificación de comprobantes es pública (sin login).
-- Necesita poder leer sales, sale_items, company_profile y clients.

DO $$
DECLARE
  t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY['sales','sale_items','company_profile','clients'])
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS "anon_select" ON %I', t);
    EXECUTE format('CREATE POLICY "anon_select" ON %I FOR SELECT TO anon USING (true)', t);
  END LOOP;
END $$;

-- ==========================================
-- FUNCIÓN PARA DESCONTAR STOCK (ATÓMICO)
-- ==========================================
-- Evita race conditions cuando múltiples cajeros venden al mismo tiempo.
CREATE OR REPLACE FUNCTION decrement_stock(p_product_id BIGINT, p_quantity INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE products
  SET stock = GREATEST(0, stock - p_quantity)
  WHERE id = p_product_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
