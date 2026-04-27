import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearToken } from '../api/client';

const NAV_ITEMS = [
  { to: '/',        label: 'Статус',     exact: true },
  { to: '/devices', label: 'Устройства', exact: false },
  { to: '/logs',    label: 'Логи',       exact: false },
];

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    clearToken();
    navigate('/login', { replace: true });
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b-2 border-blue-700 bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          {/* Logo / Brand */}
          <span className="text-xl font-black tracking-tight text-blue-800 select-none">
            IoT Gateway
          </span>

          {/* Nav */}
          <nav className="flex gap-1" aria-label="Основная навигация">
            {NAV_ITEMS.map(({ to, label, exact }) => (
              <NavLink
                key={to}
                to={to}
                end={exact}
                className={({ isActive }) =>
                  [
                    'rounded-md px-4 py-2 text-base font-bold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
                    isActive
                      ? 'bg-blue-700 text-white'
                      : 'text-gray-700 hover:bg-blue-50 hover:text-blue-800',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Logout — pushed to right */}
          <button
            onClick={handleLogout}
            className="ml-auto rounded-md border-2 border-orange-500 bg-white px-4 py-1.5 text-sm font-bold text-orange-600 hover:bg-orange-500 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400 focus-visible:ring-offset-2 transition-colors"
          >
            Выйти
          </button>
        </div>
      </header>

      {/* ── Page content ───────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
