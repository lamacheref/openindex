import { useState, useEffect } from 'react';
import PocketBase from 'pocketbase';

const pb = new PocketBase(import.meta.env.VITE_POCKETBASE_URL || 'http://localhost:8090');

export function useAuth() {
  const [user, setUser] = useState(pb.authStore.model);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Vérifier si l'utilisateur est connecté
    const unsubscribe = pb.authStore.onChange((token, model) => {
      setUser(model);
      setIsAdmin(model?.isAdmin || false);
      setLoading(false);
    });

    // Vérification initiale
    if (pb.authStore.isValid) {
      setIsAdmin(pb.authStore.model?.isAdmin || false);
    }
    setLoading(false);

    return () => unsubscribe();
  }, []);

  const login = async (email, password) => {
    try {
      const authData = await pb.collection('users').authWithPassword(email, password);
      setUser(authData.record);
      setIsAdmin(authData.record.isAdmin || false);
      return { success: true, user: authData.record };
    } catch (error) {
      console.error('Login failed:', error);
      return { success: false, error: error.message };
    }
  };

  const logout = () => {
    pb.authStore.clear();
    setUser(null);
    setIsAdmin(false);
  };

  const register = async (email, password, name) => {
    try {
      const data = {
        email,
        password,
        passwordConfirm: password,
        name,
        isAdmin: false
      };
      
      const record = await pb.collection('users').create(data);
      return { success: true, user: record };
    } catch (error) {
      console.error('Registration failed:', error);
      return { success: false, error: error.message };
    }
  };

  return {
    user,
    isAdmin,
    loading,
    login,
    logout,
    register,
    isAuthenticated: !!user
  };
}

export { pb };