import { useState, useCallback } from 'react';
import { login as apiLogin, logout as apiLogout, setToken, clearToken, isAuthenticated } from '../api/client';

export function useAuth() {
  const [authed, setAuthed] = useState<boolean>(isAuthenticated());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiLogin(username, password);
      setToken(data.access_token);
      setAuthed(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка входа');
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try { await apiLogout(); } catch {}
    clearToken();
    setAuthed(false);
  }, []);

  return { authed, loading, error, login, logout };
}
