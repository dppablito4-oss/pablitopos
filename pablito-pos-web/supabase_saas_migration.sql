-- ==========================================
-- SCRIPT DE MIGRACIÓN: PABLITO POS SAAS (NIVEL 2)
-- ==========================================

-- 1. Crear Tabla de Perfiles de Usuario (RBAC)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  company_id BIGINT REFERENCES public.company_profile(id) ON DELETE SET NULL,
  role TEXT DEFAULT 'cajero' CHECK (role IN ('superadmin', 'admin', 'cajero')),
  full_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Habilitar RLS en profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- 2. Crear Tabla de Invitaciones Auto-Destructibles
CREATE TABLE IF NOT EXISTS public.invitations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT,
  is_used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Habilitar RLS en invitations
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;

-- 3. Adaptar Tablas Existentes para Soporte Multi-Tenant
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id);
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id);
ALTER TABLE public.fiados ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id);
ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id);

-- 4. Adaptar Tabla de Configuración (Settings) para ser Multi-Tenant
-- (Para que cada empresa tenga su propio PIN, onboarding, etc.)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'settings_pkey' 
        AND conrelid = 'public.settings'::regclass
    ) THEN
        ALTER TABLE public.settings DROP CONSTRAINT settings_pkey;
    END IF;
END $$;

ALTER TABLE public.settings ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id);

-- Asignar todos los registros existentes a la empresa con ID 1 (Grafiplot)
UPDATE public.company_profile SET id = 1 WHERE id IS NOT NULL;
UPDATE public.products SET company_id = 1 WHERE company_id IS NULL;
UPDATE public.clients SET company_id = 1 WHERE company_id IS NULL;
UPDATE public.sales SET company_id = 1 WHERE company_id = 1 OR company_id IS NULL;
UPDATE public.fiados SET company_id = 1 WHERE company_id IS NULL;
UPDATE public.audit_logs SET company_id = 1 WHERE company_id IS NULL;
UPDATE public.settings SET company_id = 1 WHERE company_id IS NULL;

-- Forzar que company_id no sea nulo en settings y recrear llave primaria compuesta
ALTER TABLE public.settings ALTER COLUMN company_id SET NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'settings_pkey' 
        AND conrelid = 'public.settings'::regclass
    ) THEN
        ALTER TABLE public.settings ADD PRIMARY KEY (company_id, key);
    END IF;
END $$;

-- 5. Trigger Automatizado para Enlace y Auto-Asignación del Primer Admin
-- (Hace que el primer usuario registrado sea SuperAdmin de Grafiplot automáticamente)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.profiles) THEN
    -- Primer usuario de la base de datos es el dueño
    INSERT INTO public.profiles (id, company_id, role, full_name)
    VALUES (new.id, 1, 'superadmin', COALESCE(new.raw_user_meta_data->>'full_name', 'Super Admin'));
  ELSE
    -- Siguientes usuarios creados por defecto como cajeros (sin empresa hasta asignarse o registrarse por invitación)
    INSERT INTO public.profiles (id, company_id, role, full_name)
    VALUES (new.id, NULL, 'cajero', COALESCE(new.raw_user_meta_data->>'full_name', 'Usuario'));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Migrar usuarios de Supabase Auth ya existentes al perfil
INSERT INTO public.profiles (id, company_id, role, full_name)
SELECT id, 1, 'superadmin', COALESCE(raw_user_meta_data->>'full_name', 'Super Admin')
FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- 6. POLÍTICAS DE ACCESO RLS DE NIVEL 2 (Aislamiento Total Multi-Tenant)
-- Nota: La verificación pública anon puede seguir viendo ventas cruzadas por verificación de QR,
-- pero los usuarios normales del panel solo ven su propia empresa.

-- Habilitar RLS en todo
ALTER TABLE public.company_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sale_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fiados ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fiado_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Limpiar políticas antiguas
DO $$
DECLARE
  t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'profiles','invitations','company_profile','clients','products',
    'sales','sale_items','fiados','fiado_items','settings','audit_logs'
  ])
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS "auth_all" ON public.%I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_select" ON public.%I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_insert" ON public.%I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_update" ON public.%I', t);
    EXECUTE format('DROP POLICY IF EXISTS "auth_delete" ON public.%I', t);
    EXECUTE format('DROP POLICY IF EXISTS "anon_select" ON public.%I', t);
  END LOOP;
END $$;

-- 6.1 POLÍTICAS PARA PROFILES
CREATE POLICY "superadmin_manage_profiles" ON public.profiles FOR ALL TO authenticated 
  USING ((SELECT role FROM public.profiles WHERE id = auth.uid()) = 'superadmin');
CREATE POLICY "users_read_own_profile" ON public.profiles FOR SELECT TO authenticated 
  USING (id = auth.uid());

-- 6.2 POLÍTICAS PARA INVITATIONS
CREATE POLICY "superadmin_manage_invitations" ON public.invitations FOR ALL TO authenticated 
  USING ((SELECT role FROM public.profiles WHERE id = auth.uid()) = 'superadmin');
CREATE POLICY "anon_read_invitation" ON public.invitations FOR SELECT TO anon USING (is_used = FALSE);

-- 6.3 POLÍTICAS MULTI-TENANT (Filtro estricto por company_id)
-- Permite acceso total a los administradores/cajeros autenticados SI coincide con su company_id.

-- COMPANY_PROFILE
CREATE POLICY "auth_manage_own_company" ON public.company_profile FOR ALL TO authenticated
  USING (id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));
CREATE POLICY "superadmin_read_all_companies" ON public.company_profile FOR SELECT TO authenticated
  USING ((SELECT role FROM public.profiles WHERE id = auth.uid()) = 'superadmin');
CREATE POLICY "anon_read_company" ON public.company_profile FOR SELECT TO anon USING (is_active = TRUE);

-- CLIENTS
CREATE POLICY "auth_manage_own_clients" ON public.clients FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));
CREATE POLICY "anon_read_clients" ON public.clients FOR SELECT TO anon USING (TRUE);

-- PRODUCTS
CREATE POLICY "auth_manage_own_products" ON public.products FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));

-- SALES
CREATE POLICY "auth_manage_own_sales" ON public.sales FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));
CREATE POLICY "anon_read_sales" ON public.sales FOR SELECT TO anon USING (TRUE);

-- SALE_ITEMS
CREATE POLICY "auth_manage_own_sale_items" ON public.sale_items FOR ALL TO authenticated
  USING (
    sale_id IN (
      SELECT id FROM public.sales 
      WHERE company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid())
    )
  );
CREATE POLICY "anon_read_sale_items" ON public.sale_items FOR SELECT TO anon USING (TRUE);

-- FIADOS
CREATE POLICY "auth_manage_own_fiados" ON public.fiados FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));

-- FIADO_ITEMS
CREATE POLICY "auth_manage_own_fiado_items" ON public.fiado_items FOR ALL TO authenticated
  USING (
    fiado_id IN (
      SELECT id FROM public.fiados 
      WHERE company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid())
    )
  );

-- SETTINGS
CREATE POLICY "auth_manage_own_settings" ON public.settings FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));

-- AUDIT_LOGS
CREATE POLICY "auth_manage_own_logs" ON public.audit_logs FOR ALL TO authenticated
  USING (company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid()));
