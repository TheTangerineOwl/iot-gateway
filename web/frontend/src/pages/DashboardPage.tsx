import { useState } from 'react';
import { getGatewayStatus, getGatewayConfig, GatewayStatus, GatewayConfig } from '../api/client';
import { useFetch } from '../hooks/useFetch';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

function fmt(val: unknown): string {
  if (val == null) return '—';
  if (typeof val === 'boolean') return val ? 'да' : 'нет';
  return String(val);
}

function formatUptime(seconds?: number): string {
  if (seconds == null) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}ч ${m}м ${s}с`;
}

function formatDatetime(dt?: string): string {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleString('ru-RU', { hour12: false });
  } catch {
    return dt;
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-1.5">{title}</h2>
      <div className="border border-gray-200 rounded bg-white divide-y divide-gray-100">
        {children}
      </div>
    </section>
  );
}

function Row({ label, value, dot }: { label: string; value: React.ReactNode; dot?: boolean | null }) {
  return (
    <div className="flex items-start justify-between px-3 py-1.5 gap-4 text-xs">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className="text-gray-800 text-right flex items-center gap-2">
        {dot != null && <StatusDot ok={dot} />}
        {value}
      </span>
    </div>
  );
}

function StatusBlock({ status }: { status: GatewayStatus }) {
  const { general, devices, bus, pipeline, adapters, uptime_seconds } = status;

  return (
    <>
      <Section title="Шлюз">
        <Row label="Имя" value={fmt(general?.name)} />
        <Row label="ID" value={fmt(general?.id)} />
        <Row label="Запущен" value={fmt(general?.running)} dot={general?.running} />
        <Row label="Старт" value={formatDatetime(general?.start_time)} />
        {uptime_seconds != null && <Row label="Uptime" value={formatUptime(uptime_seconds)} />}
      </Section>

      <Section title="Устройства">
        <Row label="Всего" value={fmt(devices?.total)} />
        <Row label="Online" value={fmt(devices?.online_count)} />
      </Section>

      <Section title="Очередь сообщений">
        <Row label="Опубликовано" value={fmt(bus?.published)} />
        <Row label="Доставлено" value={fmt(bus?.delivered)} />
        <Row label="Ошибки" value={fmt(bus?.errors)} />
        <Row label="В очереди" value={`${fmt(bus?.queue_size)} / ${fmt(bus?.max_queue)}`} />
        <Row label="Подписчики" value={fmt(bus?.subscribers)} />
      </Section>

      <Section title="Pipeline">
        <Row label="Этапы" value={fmt(pipeline?.stages)} />
        <Row label="Обработано" value={fmt(pipeline?.processed)} />
        <Row label="Отфильтровано" value={fmt(pipeline?.filtered)} />
        <Row label="Ошибки" value={fmt(pipeline?.errors)} />
      </Section>

      {adapters && Object.keys(adapters).length > 0 && (
        <Section title="Адаптеры">
          {Object.entries(adapters).map(([name, a]) => (
            <Row
              key={name}
              label={name.toUpperCase()}
              dot={a.running}
              value={
                <span className="flex flex-col items-end gap-0.5">
                  <span>{a.running ? 'running' : 'stopped'}</span>
                  {a.connections != null && <span className="text-gray-400">conn: {a.connections}</span>}
                  {a.connected != null && <span className="text-gray-400">broker: {a.connected ? 'ok' : 'off'}</span>}
                </span>
              }
            />
          ))}
        </Section>
      )}
    </>
  );
}

function ConfigBlock({ config }: { config: GatewayConfig }) {
  const g = config.general_config;
  const adapters = config.adapter_configs;

  return (
    <>
      {g?.general && (
        <Section title="Конфигурация шлюза">
          <Row label="Имя" value={fmt(g.general.name)} />
          <Row label="ID" value={fmt(g.general.id)} />
          <Row label="Хранилище" value={fmt(g.general.storage)} />
        </Section>
      )}

      {g?.devices && (
        <Section title="Реестр устройств">
          <Row label="Макс. устройств" value={fmt(g.devices.max_devices)} />
          <Row label="Таймаут stale (с)" value={fmt(g.devices.timeout_stale)} />
          <Row label="Интервал проверки (с)" value={fmt(g.devices.check_interval)} />
        </Section>
      )}

      {g?.bus && (
        <Section title="Шина сообщений">
          <Row label="Макс. очередь" value={fmt(g.bus.max_queue)} />
          <Row label="Таймаут (с)" value={fmt(g.bus.timeout)} />
        </Section>
      )}

      {g?.logger && (
        <Section title="Логирование">
          <Row label="Директория" value={fmt(g.logger.dir)} />
          <Row label="Уровень" value={fmt(g.logger.level)} />
          <Row label="Debug" value={fmt(g.logger.debug)} dot={g.logger.debug ?? null} />
        </Section>
      )}

      {adapters && Object.keys(adapters).length > 0 && (
        <Section title="Адаптеры">
          {Object.entries(adapters).map(([name, a]) => (
            <Row
              key={name}
              label={name.toUpperCase()}
              dot={a.enabled}
              value={
                <span className="flex flex-col items-end gap-0.5">
                  {a.host && a.port && <span>{a.host}:{a.port}</span>}
                  {a.url_root && <span className="text-gray-400">{String(a.url_root)}</span>}
                  {a.timeout_reject != null && <span className="text-gray-400">reject: {String(a.timeout_reject)}с</span>}
                </span>
              }
            />
          ))}
        </Section>
      )}
    </>
  );
}

export default function DashboardPage() {
  const statusQ = useFetch(() => getGatewayStatus(), []);
  const configQ = useFetch(() => getGatewayConfig(), []);
  const [tab, setTab] = useState<'status' | 'config'>('status');

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="font-semibold text-gray-800">Статус шлюза</h1>
        <div className="flex gap-1">
          {(['status', 'config'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-xs px-3 py-1 rounded border transition-colors ${
                tab === t
                  ? 'bg-gray-800 text-white border-gray-800'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
              }`}
            >
              {t === 'status' ? 'Статус' : 'Конфигурация'}
            </button>
          ))}
          <button
            onClick={() => { statusQ.refetch(); configQ.refetch(); }}
            className="text-xs px-3 py-1 rounded border border-gray-200 bg-white text-gray-500 hover:border-gray-400 ml-2"
            title="Обновить"
          >
            ↻
          </button>
        </div>
      </div>

      {tab === 'status' && (
        statusQ.loading ? <Spinner /> :
        statusQ.error ? <ErrorBox message={statusQ.error} onRetry={statusQ.refetch} /> :
        statusQ.data ? <StatusBlock status={statusQ.data} /> :
        null
      )}

      {tab === 'config' && (
        configQ.loading ? <Spinner /> :
        configQ.error ? <ErrorBox message={configQ.error} onRetry={configQ.refetch} /> :
        configQ.data ? <ConfigBlock config={configQ.data} /> :
        null
      )}
    </div>
  );
}
