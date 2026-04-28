import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, setToken } from '../api/client';

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl border-2 border-gray-200 shadow-md p-8">
          <h1 className="text-2xl font-black text-gray-900 mb-1">IoT Gateway</h1>
          <p className="text-sm text-gray-500 mb-6 font-semibold">Войдите в систему</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-black text-gray-600 uppercase tracking-wide mb-1">
                Логин
              </label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoFocus
                className="w-full rounded-lg border-2 border-gray-200 px-3 py-2 text-sm font-semibold text-gray-900 focus:outline-none focus:border-blue-500 transition-colors"
                placeholder="username"
              />
            </div>

            <div>
              <label className="block text-xs font-black text-gray-600 uppercase tracking-wide mb-1">
                Пароль
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full rounded-lg border-2 border-gray-200 px-3 py-2 text-sm font-semibold text-gray-900 focus:outline-none focus:border-blue-500 transition-colors"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="text-sm font-bold text-red-600 bg-red-50 rounded-lg border border-red-200 px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-1 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-black text-white hover:bg-blue-700 disabled:opacity-60 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              {loading ? 'Вход…' : 'Войти'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
