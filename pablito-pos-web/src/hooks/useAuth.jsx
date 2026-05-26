import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext({});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async (userId) => {
    if (!userId) {
      setProfile(null);
      return;
    }
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single();
      if (!error && data) {
        setProfile(data);
      } else {
        setProfile(null);
      }
    } catch (err) {
      console.error('Error fetching user profile:', err);
      setProfile(null);
    }
  };

  useEffect(() => {
    let mounted = true;

    // Timeout de seguridad: Si Supabase o la red tardan más de 4 segundos,
    // forzar loading a false para que la app no se quede colgada en "Verificando sesión..."
    const timeoutId = setTimeout(() => {
      if (mounted) {
        console.warn("⏱️ Auth timeout: Forzando fin de verificación de sesión.");
        setLoading(false);
      }
    }, 4000);

    // Obtener sesión actual al cargar
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!mounted) return;
      const activeUser = session?.user ?? null;
      setUser(activeUser);
      if (activeUser) {
        await fetchProfile(activeUser.id);
      }
      clearTimeout(timeoutId);
      setLoading(false);
    }).catch(err => {
      console.error("Error getting session:", err);
      if (mounted) {
        clearTimeout(timeoutId);
        setLoading(false);
      }
    });

    // Escuchar cambios de autenticación (login, logout, refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (!mounted) return;
        const activeUser = session?.user ?? null;
        setUser(activeUser);
        if (activeUser) {
          await fetchProfile(activeUser.id);
        } else {
          setProfile(null);
        }
        clearTimeout(timeoutId);
        setLoading(false); // Forzar fin de carga en cambio de estado auth
      }
    );

    return () => {
      mounted = false;
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, []);

  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
    // Forzar carga de perfil tras login exitoso
    if (data?.user) {
      await fetchProfile(data.user.id);
    }
    return data;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setProfile(null);
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};
