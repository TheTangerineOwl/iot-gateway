import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getDevice, sendCommand } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [limit, setLimit] = useState(20);
  const [command, setCommand] = useState('');
  const [params, setParams] = useState('');
  const [cmdResult, setCmdResult] = useState<string | null>(null);
  const [cmdError, setCmdError] = useState<string | null>(null);
  const [cmdLoading, setCmdLoading] = useState(false);

  const { data, loading, error, refetch } = useFetch(
    () => getDevice(deviceId!, limit),
    [deviceId, limit]
  );

  async function handleSendCommand(e: React.FormEvent) {
    e.preventDefault();
    if (!deviceId || !command.trim()) return;
    setCmdResult(null);
    setCmdError(null);
    setCmdLoading(true);
    try {
      let parsedParams: Record<string, unknown> | undefined;
      if (params.trim()) {
        parsedParams = JSON.parse(params);
      }
      const res = await sendCommand(deviceId, { command: command.trim(), params: parsedParams });
      setCmdResult(JSON.stringify(res, null, 2));
    } catch (e) {
      setCmdError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setCmdLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <button onClick={() => navigate('/devices')} className="text-xs text-gray-400 hover:text-gray-700">← Назад</button>
        <h2 className="font-semibold text-gray-800 font-mono">{deviceId}</h2>
      </div>

      {loading && <Spinner label="Загрузка…" />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {data && (
        <>
          {/* Device info */}
          <div className="border border-gray-200 rounded bg-white p-4 text-xs flex flex-col gap-1">
            <div className="flex justify-between"><span className="text-gray-400">Имя</span><span>{data.device.name ?? '—'}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Протокол</span><span>{data.device.protocol ?? '—'}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Зарегистрирован</span><span>{data.device.registered_at ? new Date(data.device.registered_at).toLocaleString('ru') : '—'}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Последний визит</span><span>{data.device.last_seen ? new Date(data.device.last_seen).toLocaleString('ru') : '—'}</span></div>
          </div>

          {/* Telemetry */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-gray-600">
                Телеметрия <span className="font-normal text-gray-400">({data.telemetry.total})</span>
              </h3>
              <div className="flex items-center gap-2">
                <select
                  value={limit}
                  onChange={e => setLimit(Number(e.target.value))}
                  className="border border-gray-200 rounded px-2 py-0.5 text-xs bg-white"
                >
                  {[10, 20, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
                <button onClick={refetch} className="text-xs text-gray-400 hover:text-gray-700">↺</button>
              </div>
            </div>
            {data.telemetry.records.length === 0 ? (
              <p className="text-xs text-gray-400">Нет записей.</p>
            ) : (
              <div className="border border-gray-200 rounded bg-white overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left px-3 py-2 text-gray-500 font-medium">Время</th>
                      <th className="text-left px-3 py-2 text-gray-500 font-medium">Данные</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.telemetry.records.map((r, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                          {new Date(r.timestamp).toLocaleString('ru')}
                        </td>
                        <td className="px-3 py-2 font-mono text-gray-700">
                          {JSON.stringify(r.payload)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Send command */}
          <div className="border border-gray-200 rounded bg-white p-4 flex flex-col gap-3">
            <h3 className="text-xs font-semibold text-gray-600">Отправить команду</h3>
            <form onSubmit={handleSendCommand} className="flex flex-col gap-2 text-xs">
              <label className="flex flex-col gap-0.5 text-gray-500">
                Команда
                <input
                  value={command}
                  onChange={e => setCommand(e.target.value)}
                  placeholder="ping"
                  className="border border-gray-200 rounded px-2 py-1 bg-white font-mono"
                />
              </label>
              <label className="flex flex-col gap-0.5 text-gray-500">
                Параметры (JSON)
                <input
                  value={params}
                  onChange={e => setParams(e.target.value)}
                  placeholder='{"key": "value"}'
                  className="border border-gray-200 rounded px-2 py-1 bg-white font-mono"
                />
              </label>
              <button
                type="submit"
                disabled={cmdLoading || !command.trim()}
                className="self-start px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {cmdLoading ? 'Отправка…' : 'Отправить'}
              </button>
            </form>
            {cmdError && <ErrorBox message={cmdError} />}
            {cmdResult && (
              <pre className="bg-gray-900 text-green-400 rounded p-2 text-[11px] font-mono overflow-x-auto">
                {cmdResult}
              </pre>
            )}
          </div>
        </>
      )}
    </div>
  );
}
