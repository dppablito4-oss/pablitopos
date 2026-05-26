-- ========================================================
-- PARCHE FASE 3: EMAIL EN PERFILES Y REGISTRO DE CAJEROS
-- ========================================================

-- 1. Agregar columna email a la tabla profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email TEXT;

-- 2. Migrar los emails de los usuarios existentes
UPDATE public.profiles p 
SET email = (SELECT u.email FROM auth.users u WHERE u.id = p.id)
WHERE p.email IS NULL;

-- 3. Actualizar la función handle_new_user para guardar el email automáticamente al registrarse
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.profiles) THEN
    -- Primer usuario de la base de datos es el dueño
    INSERT INTO public.profiles (id, company_id, role, full_name, email)
    VALUES (new.id, 1, 'superadmin', COALESCE(new.raw_user_meta_data->>'full_name', 'Super Admin'), new.email);
  ELSE
    -- Por defecto se registra como cajero y se vincula en el formulario de Onboarding
    INSERT INTO public.profiles (id, company_id, role, full_name, email)
    VALUES (new.id, NULL, 'cajero', COALESCE(new.raw_user_meta_data->>'full_name', 'Usuario'), new.email);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
