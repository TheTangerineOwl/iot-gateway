import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, setToken } from '../api/client';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(username, password);
      setToken(res.access_token);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 font-mono text-sm">
      <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded p-6 w-72 flex flex-col gap-3">
        <h1 className="font-semibold text-gray-700 text-base">IoT Gateway</h1>
        {error && (
          <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
            {error}
          </div>
        )}
        <label className="flex flex-col gap-0.5 text-xs text-gray-500">
          Логин
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="border border-gray-200 rounded px-2 py-1 bg-white text-gray-900"
            autoFocus
          />
        </label>
        <label className="flex flex-col gap-0.5 text-xs text-gray-500">
          Пароль
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="border border-gray-200 rounded px-2 py-1 bg-white text-gray-900"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="mt-1 px-3 py-1.5 rounded bg-blue-600 text-white text-xs hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Вход…' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
