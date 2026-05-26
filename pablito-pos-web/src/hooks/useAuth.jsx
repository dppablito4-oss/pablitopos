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
      if (error) {
        console.error("Supabase profiles query error:", error);
        setProfile(null);
      } else if (data) {
        setProfile(data);
      } else {
        setProfile(null);
      }
    } catch (err) {
      console.error('Error fetching user profile exception:', err);
      setProfile(null);
    }
  };

  useEffect(() => {
    let mounted = true;

    // Timeout de seguridad: 6 segundos por si Supabase está frío o hay problemas de red
    const timeoutId = setTimeout(() => {
      if (mounted) {
        console.warn("⏱️ Auth timeout: Forzando fin de verificación de sesión.");
        setLoading(false);
      }
    }, 6000);

    // Obtener sesión de forma aislada al inicializar la app
    const initAuth = async () => {
      try {
        const { data: { session }, error: sessionErr } = await supabase.auth.getSession();
        if (sessionErr) throw sessionErr;
        
        if (!mounted) return;
        const activeUser = session?.user ?? null;
        setUser(activeUser);
        if (activeUser) {
          await fetchProfile(activeUser.id);
        }
      } catch (err) {
        console.error("Error in initAuth session load:", err);
      } finally {
        if (mounted) {
          clearTimeout(timeoutId);
          setLoading(false);
        }
      }
    };

    initAuth();

    // Escuchar futuros cambios de sesión, pero SIN apagar loading de forma prematura
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (!mounted) return;
        const activeUser = session?.user ?? null;
        setUser(activeUser);
        
        if (activeUser) {
          await fetchProfile(activeUser.id);
        } else {
          setProfile(null);
        }

        // Si es un logout explícito o login exitoso posterior, asegurar apagar loading
        if (event === 'SIGNED_OUT' || event === 'SIGNED_IN') {
          clearTimeout(timeoutId);
          setLoading(false);
        }
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
