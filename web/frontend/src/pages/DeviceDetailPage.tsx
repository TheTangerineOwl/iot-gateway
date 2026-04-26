import { useState, FormEvent } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getDevice, sendCommand, TelemetryRecord, CommandRequest } from '../api/client';
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
  return Date.now() - new Date(lastSeen).getTime() < 2 * 60 * 1000;
}

function TelemetryRow({ rec }: { rec: TelemetryRecord }) {
  return (
    <tr className="border-b border-gray-100 text-xs align-top">
      <td className="px-3 py-1.5 text-gray-400 whitespace-nowrap">{formatDt(rec.timestamp)}</td>
      <td className="px-3 py-1.5 text-gray-700">
        <pre className="whitespace-pre-wrap break-all font-mono text-[11px]">
          {JSON.stringify(rec.payload, null, 2)}
        </pre>
      </td>
    </tr>
  );
}

function CommandPanel({ deviceId }: { deviceId: string }) {
  const [cmd, setCmd] = useState('');
  const [params, setParams] = useState('');
  const [timeout, setTimeout2] = useState('10');
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setResult(null);
    setErr(null);
    setLoading(true);
    try {
      let parsedParams: Record<string, unknown> | undefined;
      if (params.trim()) {
        parsedParams = JSON.parse(params);
      }
      const body: CommandRequest = {
        command: cmd,
        params: parsedParams,
        timeout: parseFloat(timeout) || 10,
      };
      const res = await sendCommand(deviceId, body);
      setResult(JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-6">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">
        Отправить команду
      </h2>
      <form onSubmit={handleSubmit} className="border border-gray-200 rounded bg-white p-3 flex flex-col gap-2">
        <div className="flex gap-2">
          <label className="flex flex-col gap-0.5 text-xs text-gray-500 flex-1">
            Команда *
            <input
              value={cmd}
              onChange={e => setCmd(e.target.value)}
              required
              placeholder="ping"
              className="border border-gray-300 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-blue-400"
            />
          </label>
          <label className="flex flex-col gap-0.5 text-xs text-gray-500 w-20">
            Таймаут (с)
            <input
              value={timeout}
              onChange={e => setTimeout2(e.target.value)}
              type="number"
              min="0"
              className="border border-gray-300 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-blue-400"
            />
          </label>
        </div>
        <label className="flex flex-col gap-0.5 text-xs text-gray-500">
          Параметры (JSON, необязательно)
          <textarea
            value={params}
            onChange={e => setParams(e.target.value)}
            rows={2}
            placeholder='{"key": "value"}'
            className="border border-gray-300 rounded px-2 py-1 text-xs font-mono resize-none focus:outline-none focus:border-blue-400"
          />
        </label>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading || !cmd.trim()}
            className="text-xs px-3 py-1.5 rounded bg-gray-800 text-white hover:bg-gray-700 disabled:opacity-50"
          >
            {loading ? 'Отправка…' : 'Отправить'}
          </button>
          {err && <span className="text-red-600 text-xs">{err}</span>}
        </div>
        {result && (
          <pre className="mt-1 text-[11px] font-mono bg-gray-50 border border-gray-200 rounded p-2 whitespace-pre-wrap break-all text-gray-700">
            {result}
          </pre>
        )}
      </form>
    </section>
  );
}

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const [limit, setLimit] = useState(20);

  const { data, loading, error, refetch } = useFetch(
    () => getDevice(deviceId!, limit),
    [deviceId, limit]
  );

  const device = data?.device;
  const telemetry = data?.telemetry;
  const online = isOnline(device?.last_seen);

  return (
    <div>
      <div className="flex items-center gap-2 mb-4 text-xs text-gray-400">
        <Link to="/devices" className="hover:text-gray-700">← Устройства</Link>
        <span>/</span>
        <span className="text-gray-700 font-medium">{deviceId}</span>
      </div>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {device && (
        <>
          {/* Info */}
          <section className="mb-5">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-1.5">Устройство</h2>
            <div className="border border-gray-200 rounded bg-white divide-y divide-gray-100">
              {[
                ['ID', device.device_id],
                ['Имя', device.name ?? '—'],
                ['Протокол', device.protocol ?? '—'],
                ['Зарегистрировано', formatDt(device.registered_at)],
                ['Последняя активность', formatDt(device.last_seen)],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between px-3 py-1.5 text-xs">
                  <span className="text-gray-500">{label}</span>
                  <span className="text-gray-800">{value}</span>
                </div>
              ))}
              <div className="flex justify-between px-3 py-1.5 text-xs">
                <span className="text-gray-500">Статус</span>
                <span className="flex items-center gap-1.5">
                  <StatusDot ok={online} />
                  <span className="text-gray-800">{online == null ? '?' : online ? 'online' : 'offline'}</span>
                </span>
              </div>
              {device.metadata && Object.keys(device.metadata).length > 0 && (
                <div className="flex justify-between px-3 py-1.5 text-xs">
                  <span className="text-gray-500">Metadata</span>
                  <pre className="text-[11px] text-gray-600 font-mono text-right">
                    {JSON.stringify(device.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </section>

          {/* Telemetry */}
          <section className="mb-5">
            <div className="flex items-center justify-between mb-1.5">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
                Телеметрия{telemetry ? ` (${telemetry.total})` : ''}
              </h2>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 flex items-center gap-1">
                  строк:
                  <select
                    value={limit}
                    onChange={e => setLimit(Number(e.target.value))}
                    className="border border-gray-200 rounded px-1 py-0.5 text-xs bg-white"
                  >
                    {[10, 20, 50, 100].map(n => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </label>
                <button
                  onClick={refetch}
                  className="text-xs px-2 py-0.5 rounded border border-gray-200 bg-white text-gray-500 hover:border-gray-400"
                  title="Обновить"
                >↻</button>
              </div>
            </div>

            {telemetry && telemetry.records.length === 0 ? (
              <p className="text-xs text-gray-400">Нет записей телеметрии.</p>
            ) : (
              <div className="overflow-x-auto border border-gray-200 rounded bg-white">
                <table className="w-full text-left">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      {['Время', 'Данные'].map(h => (
                        <th key={h} className="px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-gray-500">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {telemetry?.records.map((rec, i) => (
                      <TelemetryRow key={i} rec={rec} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <CommandPanel deviceId={deviceId!} />
        </>
      )}
    </div>
  );
}
