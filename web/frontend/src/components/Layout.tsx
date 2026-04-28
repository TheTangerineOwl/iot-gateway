import { NavLink, useNavigate } from 'react-router-dom';
import { clearToken, logout } from '../api/client';

const NAV_ITEMS = [
  { to: '/', label: 'Дашборд', end: true },
  { to: '/devices', label: 'Устройства', end: false },
  { to: '/logs', label: 'Логи', end: false },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // игнорируем ошибки при логауте (например, если токен уже протух)
    } finally {
      clearToken();
      navigate('/login', { replace: true });
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b-2 border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex h-14 items-center justify-between gap-4">
          <span className="text-lg font-black text-gray-900 tracking-tight">
            IoT Gateway
          </span>
          <nav className="flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  [
                    'px-3 py-1.5 rounded-lg text-sm font-bold transition-colors',
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 hover:bg-gray-100',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <button
            onClick={handleLogout}
            className="text-sm font-bold text-gray-500 hover:text-red-600 transition-colors px-2 py-1"
          >
            Выйти
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {children}
      </main>
    </div>
  );
}
