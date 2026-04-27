import { useNavigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getDevices } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

export default function DevicesPage() {
  const { data, loading, error, refetch } = useFetch(() => getDevices(), []);
  const navigate = useNavigate();

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-black text-gray-900">
          Устройства{' '}
          {data ? (
            <span className="text-lg font-bold text-gray-500">({data.total})</span>
          ) : null}
        </h1>
        <button
          onClick={refetch}
          className="flex items-center gap-2 rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
        >
          ↺ Обновить
        </button>
      </div>

      {loading && <Spinner label="Загрузка…" />}
      {error   && <ErrorBox message={error} onRetry={refetch} />}

      {data && data.devices.length === 0 && (
        <p className="rounded-xl border-2 border-dashed border-gray-300 p-8 text-center text-base font-semibold text-gray-500">
          Устройства не найдены.
        </p>
      )}

      {data && data.devices.length > 0 && (
        <div className="overflow-hidden rounded-xl border-2 border-gray-200 bg-white shadow-sm">
          <table className="w-full text-base">
            <thead className="border-b-2 border-gray-200 bg-gray-100">
              <tr>
                <th className="px-5 py-3 text-left text-sm font-black uppercase tracking-wide text-gray-600">
                  Статус / ID
                </th>
                <th className="px-5 py-3 text-left text-sm font-black uppercase tracking-wide text-gray-600">
                  Имя
                </th>
                <th className="px-5 py-3 text-left text-sm font-black uppercase tracking-wide text-gray-600">
                  Протокол
                </th>
                <th className="px-5 py-3 text-left text-sm font-black uppercase tracking-wide text-gray-600">
                  Последний визит
                </th>
              </tr>
            </thead>
            <tbody className="divide-y-2 divide-gray-100">
              {data.devices.map(d => (
                <tr
                  key={d.device_id}
                  onClick={() => navigate(`/devices/${encodeURIComponent(d.device_id)}`)}
                  className="cursor-pointer hover:bg-blue-50 transition-colors"
                >
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <StatusDot active={!!d.last_seen} />
                      <span className="font-mono text-sm font-bold text-gray-900">
                        {d.device_id}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3 font-semibold text-gray-800">
                    {d.name ?? <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-5 py-3">
                    {d.protocol ? (
                      <span className="inline-block rounded-md border border-blue-300 bg-blue-50 px-2 py-0.5 text-sm font-bold text-blue-800">
                        {d.protocol}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-sm font-semibold text-gray-600">
                    {d.last_seen
                      ? new Date(d.last_seen).toLocaleString('ru')
                      : <span className="text-gray-400">—</span>}
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
