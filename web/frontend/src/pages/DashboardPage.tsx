import { useFetch } from '../hooks/useFetch';
import { getGatewayStatus, getGatewayConfig, GatewayStatus } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

function uptime(seconds?: number): string {
  if (seconds == null) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}ч ${m}м ${s}с`;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-gray-200 rounded bg-white p-4 flex flex-col gap-2">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{title}</h3>
      {children}
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-xs gap-2">
      <span className="text-gray-400">{k}</span>
      <span className="text-gray-800 font-mono">{v ?? '—'}</span>
    </div>
  );
}

function StatusSection({ status }: { status: GatewayStatus }) {
  const { general, devices, bus, pipeline, adapters, uptime_seconds } = status;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <Card title="Общее">
        <KV k="ID" v={general?.id} />
        <KV k="Имя" v={general?.name} />
        <KV k="Статус" v={
          <span className="flex items-center gap-1">
            <StatusDot active={general?.running} />
            {general?.running ? 'работает' : 'остановлен'}
          </span>
        } />
        <KV k="Аптайм" v={uptime(uptime_seconds)} />
        <KV k="Запуск" v={general?.start_time ? new Date(general.start_time).toLocaleString('ru') : '—'} />
      </Card>

      <Card title="Устройства">
        <KV k="Всего" v={devices?.total} />
        <KV k="Онлайн" v={devices?.online_count} />
      </Card>

      <Card title="Шина сообщений">
        <KV k="Опубликовано" v={bus?.published} />
        <KV k="Доставлено" v={bus?.delivered} />
        <KV k="Ошибок" v={bus?.errors} />
        <KV k="Очередь" v={bus?.queue_size != null ? `${bus.queue_size} / ${bus.max_queue ?? '?'}` : '—'} />
        <KV k="Подписчиков" v={bus?.subscribers} />
      </Card>

      <Card title="Конвейер">
        <KV k="Этапов" v={pipeline?.stages} />
        <KV k="Обработано" v={pipeline?.processed} />
        <KV k="Отфильтровано" v={pipeline?.filtered} />
        <KV k="Ошибок" v={pipeline?.errors} />
      </Card>

      {adapters && Object.keys(adapters).length > 0 && (
        <Card title="Адаптеры">
          {Object.entries(adapters).map(([name, a]) => (
            <div key={name} className="flex items-center justify-between text-xs">
              <span className="text-gray-500">{name}</span>
              <span className="flex items-center gap-1 text-gray-800">
                <StatusDot active={a.running ?? a.connected} />
                {a.protocol ?? ''}
                {a.connections != null ? ` (${a.connections} соед.)` : ''}
              </span>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { data: status, loading: sl, error: se, refetch: sr } = useFetch(() => getGatewayStatus(), []);
  const { data: config, loading: cl, error: ce, refetch: cr } = useFetch(() => getGatewayConfig(), []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Статус шлюза</h2>
        <button onClick={() => { sr(); cr(); }} className="text-xs text-gray-400 hover:text-gray-700">↺ Обновить</button>
      </div>

      {(sl || cl) && <Spinner label="Загрузка…" />}
      {se && <ErrorBox message={se} onRetry={sr} />}
      {ce && <ErrorBox message={ce} onRetry={cr} />}
      {status && <StatusSection status={status} />}

      {config && (
        <div className="flex flex-col gap-2">
          <h3 className="font-semibold text-gray-700 text-xs uppercase tracking-wider">Конфигурация</h3>
          <pre className="bg-gray-900 text-gray-300 rounded p-3 text-[11px] font-mono overflow-x-auto">
            {JSON.stringify(config, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
