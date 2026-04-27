import { Navigate, useNavigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getDevices } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

export default function DevicesPage() {
  const navigate = useNavigate();
  const { data, loading, error, unauthorized, refetch } = useFetch(() => getDevices(), []);

  if (unauthorized) return <Navigate to="/login" replace />;

  const isOnline = (lastSeen?: string) => {
    if (!lastSeen) return false;
    return Date.now() - new Date(lastSeen).getTime() < 60_000;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-black text-gray-900">
          Устройства{' '}
          {data ? (
            <span className="text-xl font-semibold text-gray-400">({data.total})</span>
          ) : null}
        </h1>
        <button
          onClick={refetch}
          className="flex items-center gap-2 rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          ↺ Обновить
        </button>
      </div>

      {loading && <Spinner label="Загрузка устройств…" />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {data && data.devices.length === 0 && (
        <p className="text-gray-500 font-semibold py-8 text-center">Устройства не найдены.</p>
      )}

      {data && data.devices.length > 0 && (
        <div className="overflow-auto rounded-xl border-2 border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b-2 border-gray-200">
                <th className="px-4 py-3 text-left text-xs font-black uppercase tracking-wide text-gray-500">Статус / ID</th>
                <th className="px-4 py-3 text-left text-xs font-black uppercase tracking-wide text-gray-500">Имя</th>
                <th className="px-4 py-3 text-left text-xs font-black uppercase tracking-wide text-gray-500">Протокол</th>
                <th className="px-4 py-3 text-left text-xs font-black uppercase tracking-wide text-gray-500">Последний визит</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.devices.map(d => (
                <tr
                  key={d.device_id}
                  onClick={() => navigate(`/devices/${encodeURIComponent(d.device_id)}`)}
                  className="cursor-pointer hover:bg-blue-50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <StatusDot active={isOnline(d.last_seen)} />
                      <span className="font-mono font-bold text-gray-800">{d.device_id}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-semibold text-gray-700">{d.name ?? '—'}</td>
                  <td className="px-4 py-3">
                    {d.protocol ? (
                      <span className="inline-block rounded-full bg-blue-100 text-blue-800 border border-blue-300 px-2.5 py-0.5 text-xs font-black">
                        {d.protocol}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-semibold text-gray-600">
                    {d.last_seen ? new Date(d.last_seen).toLocaleString('ru') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
