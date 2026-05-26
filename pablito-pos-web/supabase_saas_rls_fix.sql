-- ========================================================
-- SOLUCIÓN DEFINITIVA: EVITAR RECURSIÓN INFINITA RLS
-- ========================================================

-- 1. Crear funciones auxiliares con SECURITY DEFINER para saltarse el RLS al consultar roles
CREATE OR REPLACE FUNCTION public.get_user_role(p_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER -- Importante: corre con privilegios del sistema, saltando el RLS
SET search_path = public
AS $$
BEGIN
  RETURN (SELECT role FROM public.profiles WHERE id = p_user_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.get_user_company(p_user_id UUID)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER -- Importante: corre con privilegios del sistema, saltando el RLS
SET search_path = public
AS $$
BEGIN
  RETURN (SELECT company_id FROM public.profiles WHERE id = p_user_id);
END;
$$;

-- 2. Actualizar políticas de PROFILES para evitar recursión infinita
DROP POLICY IF EXISTS "superadmin_manage_profiles" ON public.profiles;
CREATE POLICY "superadmin_manage_profiles" ON public.profiles FOR ALL TO authenticated 
  USING (public.get_user_role(auth.uid()) = 'superadmin');

DROP POLICY IF EXISTS "users_read_own_profile" ON public.profiles;
CREATE POLICY "users_read_own_profile" ON public.profiles FOR SELECT TO authenticated 
  USING (id = auth.uid());

DROP POLICY IF EXISTS "auth_update_own_profile" ON public.profiles;
CREATE POLICY "auth_update_own_profile" ON public.profiles FOR UPDATE TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- 3. Actualizar políticas de INVITATIONS
DROP POLICY IF EXISTS "superadmin_manage_invitations" ON public.invitations;
CREATE POLICY "superadmin_manage_invitations" ON public.invitations FOR ALL TO authenticated 
  USING (public.get_user_role(auth.uid()) = 'superadmin');

DROP POLICY IF EXISTS "admin_manage_cajero_invitations" ON public.invitations;
CREATE POLICY "admin_manage_cajero_invitations" ON public.invitations FOR ALL TO authenticated
  USING (
    public.get_user_role(auth.uid()) = 'superadmin'
    OR
    (
      public.get_user_role(auth.uid()) = 'admin'
      AND
      company_id = public.get_user_company(auth.uid())
    )
  );

-- 4. Actualizar políticas MULTI-TENANT para que usen las funciones rápidas
DROP POLICY IF EXISTS "auth_manage_own_company" ON public.company_profile;
CREATE POLICY "auth_manage_own_company" ON public.company_profile FOR ALL TO authenticated
  USING (id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "superadmin_read_all_companies" ON public.company_profile;
CREATE POLICY "superadmin_read_all_companies" ON public.company_profile FOR SELECT TO authenticated
  USING (public.get_user_role(auth.uid()) = 'superadmin');

DROP POLICY IF EXISTS "auth_manage_own_clients" ON public.clients;
CREATE POLICY "auth_manage_own_clients" ON public.clients FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "auth_manage_own_products" ON public.products;
CREATE POLICY "auth_manage_own_products" ON public.products FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "auth_manage_own_sales" ON public.sales;
CREATE POLICY "auth_manage_own_sales" ON public.sales FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "auth_manage_own_sale_items" ON public.sale_items;
CREATE POLICY "auth_manage_own_sale_items" ON public.sale_items FOR ALL TO authenticated
  USING (
    sale_id IN (
      SELECT id FROM public.sales 
      WHERE company_id = public.get_user_company(auth.uid())
    )
  );

DROP POLICY IF EXISTS "auth_manage_own_fiados" ON public.fiados;
CREATE POLICY "auth_manage_own_fiados" ON public.fiados FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "auth_manage_own_fiado_items" ON public.fiado_items;
CREATE POLICY "auth_manage_own_fiado_items" ON public.fiado_items FOR ALL TO authenticated
  USING (
    fiado_id IN (
      SELECT id FROM public.fiados 
      WHERE company_id = public.get_user_company(auth.uid())
    )
  );

DROP POLICY IF EXISTS "auth_manage_own_settings" ON public.settings;
CREATE POLICY "auth_manage_own_settings" ON public.settings FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "auth_manage_own_logs" ON public.audit_logs;
CREATE POLICY "auth_manage_own_logs" ON public.audit_logs FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));

DROP POLICY IF EXISTS "auth_manage_own_sequences" ON public.document_sequences;
CREATE POLICY "auth_manage_own_sequences" ON public.document_sequences FOR ALL TO authenticated
  USING (company_id = public.get_user_company(auth.uid()));
