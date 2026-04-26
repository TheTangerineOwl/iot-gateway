import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearToken } from '../api/client';

const NAV_ITEMS = [
  { to: '/', label: 'Статус', exact: true },
  { to: '/devices', label: 'Устройства' },
  { to: '/logs', label: 'Логи' },
];

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    clearToken();
    navigate('/login', { replace: true });
  }

  return (
    <div className="min-h-screen flex flex-col font-mono text-sm text-gray-900 bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-4 py-2 flex items-center gap-6">
        <span className="font-semibold text-gray-700 tracking-tight">IoT Gateway</span>
        <nav className="flex gap-4 flex-1">
          {NAV_ITEMS.map(({ to, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                isActive
                  ? 'text-blue-600 underline underline-offset-2'
                  : 'text-gray-500 hover:text-gray-800'
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="text-gray-400 hover:text-red-500 text-xs"
        >
          Выйти
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 p-4 max-w-5xl w-full mx-auto">
        <Outlet />
      </main>
    </div>
  );
}
