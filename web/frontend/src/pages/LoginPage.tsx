import { FormEvent, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, setToken, isAuthenticated } from '../api/client';

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated()) navigate('/', { replace: true });
  }, [navigate]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await login(username, password);
      setToken(data.access_token);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 font-mono">
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded p-8 w-full max-w-xs flex flex-col gap-4"
      >
        <h1 className="text-base font-semibold text-gray-800 mb-2">IoT Gateway — вход</h1>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
            {error}
          </p>
        )}

        <label className="flex flex-col gap-1 text-xs text-gray-600">
          Логин
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoComplete="username"
            className="border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-blue-400"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-gray-600">
          Пароль
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:border-blue-400"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="mt-2 bg-gray-800 text-white text-sm rounded px-4 py-2 hover:bg-gray-700 disabled:opacity-50"
        >
          {loading ? 'Вход…' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
