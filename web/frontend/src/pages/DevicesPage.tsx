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
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">
          Устройства {data ? <span className="text-gray-400 font-normal">({data.total})</span> : null}
        </h2>
        <button onClick={refetch} className="text-xs text-gray-400 hover:text-gray-700">↺ Обновить</button>
      </div>

      {loading && <Spinner label="Загрузка…" />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {data && data.devices.length === 0 && (
        <p className="text-xs text-gray-400">Устройства не найдены.</p>
      )}

      {data && data.devices.length > 0 && (
        <div className="border border-gray-200 rounded bg-white overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-3 py-2 text-gray-500 font-medium">ID</th>
                <th className="text-left px-3 py-2 text-gray-500 font-medium">Имя</th>
                <th className="text-left px-3 py-2 text-gray-500 font-medium">Протокол</th>
                <th className="text-left px-3 py-2 text-gray-500 font-medium">Последний визит</th>
              </tr>
            </thead>
            <tbody>
              {data.devices.map((d, i) => (
                <tr
                  key={d.device_id}
                  onClick={() => navigate(`/devices/${encodeURIComponent(d.device_id)}`)}
                  className={`cursor-pointer hover:bg-blue-50 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}
                >
                  <td className="px-3 py-2 font-mono text-gray-700 flex items-center gap-1">
                    <StatusDot active={!!d.last_seen} />
                    {d.device_id}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{d.name ?? '—'}</td>
                  <td className="px-3 py-2 text-gray-500">{d.protocol ?? '—'}</td>
                  <td className="px-3 py-2 text-gray-400">
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
