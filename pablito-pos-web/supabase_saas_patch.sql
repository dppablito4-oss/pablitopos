-- ==========================================
-- PARCHE DE SEGURIDAD: CONTROL DE ONBOARDING
-- ==========================================

-- 1. Permitir que usuarios logueados sin empresa puedan CREAR su primera empresa
DROP POLICY IF EXISTS "auth_insert_first_company" ON public.company_profile;
CREATE POLICY "auth_insert_first_company" ON public.company_profile FOR INSERT TO authenticated
  WITH CHECK (
    (SELECT company_id FROM public.profiles WHERE id = auth.uid()) IS NULL
  );

-- 2. Permitir que los usuarios actualicen su propio perfil (para asignarse la empresa creada y el rol admin)
DROP POLICY IF EXISTS "auth_update_own_profile" ON public.profiles;
CREATE POLICY "auth_update_own_profile" ON public.profiles FOR UPDATE TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- 3. Permitir que los clientes y anónimos actualicen una invitación únicamente para marcarla como USADA
DROP POLICY IF EXISTS "anon_update_use_invitation" ON public.invitations;
CREATE POLICY "anon_update_use_invitation" ON public.invitations FOR UPDATE TO anon, authenticated
  USING (is_used = FALSE)
  WITH CHECK (is_used = TRUE);
