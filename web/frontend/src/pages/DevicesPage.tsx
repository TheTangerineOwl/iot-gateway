import { Link } from 'react-router-dom';
import { getDevices, Device } from '../api/client';
import { useFetch } from '../hooks/useFetch';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

function formatDt(dt?: string): string {
  if (!dt) return '—';
  try { return new Date(dt).toLocaleString('ru-RU', { hour12: false }); } catch { return dt; }
}

function isOnline(lastSeen?: string): boolean | null {
  if (!lastSeen) return null;
  const diff = Date.now() - new Date(lastSeen).getTime();
  return diff < 2 * 60 * 1000; // < 2 мин — online
}

function DeviceRow({ d }: { d: Device }) {
  const online = isOnline(d.last_seen);
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 text-xs">
      <td className="px-3 py-2">
        <Link to={`/devices/${encodeURIComponent(d.device_id)}`} className="text-blue-600 hover:underline font-medium">
          {d.device_id}
        </Link>
      </td>
      <td className="px-3 py-2 text-gray-600">{d.name ?? '—'}</td>
      <td className="px-3 py-2 text-gray-500">{d.protocol ?? '—'}</td>
      <td className="px-3 py-2 text-gray-500">{formatDt(d.last_seen)}</td>
      <td className="px-3 py-2">
        <span className="flex items-center gap-1.5">
          <StatusDot ok={online} />
          <span className="text-gray-500">{online == null ? '?' : online ? 'online' : 'offline'}</span>
        </span>
      </td>
    </tr>
  );
}

export default function DevicesPage() {
  const { data, loading, error, refetch } = useFetch(() => getDevices(), []);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="font-semibold text-gray-800">
          Устройства{data ? ` (${data.total})` : ''}
        </h1>
        <button
          onClick={refetch}
          className="text-xs px-3 py-1 rounded border border-gray-200 bg-white text-gray-500 hover:border-gray-400"
          title="Обновить"
        >
          ↻
        </button>
      </div>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {data && (
        data.devices.length === 0 ? (
          <p className="text-xs text-gray-400">Нет зарегистрированных устройств.</p>
        ) : (
          <div className="overflow-x-auto border border-gray-200 rounded bg-white">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['ID', 'Имя', 'Протокол', 'Последняя активность', 'Статус'].map(h => (
                    <th key={h} className="px-3 py-2 text-gray-500 font-medium uppercase tracking-wider text-[10px]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.devices.map(d => <DeviceRow key={d.device_id} d={d} />)}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
