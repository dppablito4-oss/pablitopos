-- ========================================================
-- PARCHE FASE 3: SISTEMA DE INVITACIONES DE CAJEROS
-- ========================================================

-- 1. Agregar el tipo de invitación y company_id a la tabla de invitaciones
ALTER TABLE public.invitations ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'company' CHECK (type IN ('company', 'cajero'));
ALTER TABLE public.invitations ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES public.company_profile(id) ON DELETE CASCADE;

-- 2. Actualizar triggers y políticas de invitaciones
DROP POLICY IF EXISTS "admin_manage_cajero_invitations" ON public.invitations;
CREATE POLICY "admin_manage_cajero_invitations" ON public.invitations FOR ALL TO authenticated
  USING (
    ((SELECT role FROM public.profiles WHERE id = auth.uid()) = 'superadmin')
    OR
    (
      (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin'
      AND
      company_id = (SELECT company_id FROM public.profiles WHERE id = auth.uid())
    )
  );

-- 3. Modificar el trigger public.handle_new_user() para soportar auto-registro de cajeros si vienen de una invitación de cajero
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
  v_invite_company_id BIGINT;
  v_invite_type TEXT;
BEGIN
  -- Intentamos buscar si este usuario se registró por medio de una invitación activa
  -- (Usamos el email para cruzar el registro o una función manual tras login, 
  -- por seguridad por defecto se crea el perfil vacío y se actualiza al validar la invitación en el Onboarding)
  IF NOT EXISTS (SELECT 1 FROM public.profiles) THEN
    -- Primer usuario de la base de datos es SuperAdmin
    INSERT INTO public.profiles (id, company_id, role, full_name)
    VALUES (new.id, 1, 'superadmin', COALESCE(new.raw_user_meta_data->>'full_name', 'Super Admin'));
  ELSE
    -- Por defecto se registra como cajero y se vincula en el formulario de Onboarding
    INSERT INTO public.profiles (id, company_id, role, full_name)
    VALUES (new.id, NULL, 'cajero', COALESCE(new.raw_user_meta_data->>'full_name', 'Usuario'));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
