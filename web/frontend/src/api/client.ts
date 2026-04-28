const BASE = import.meta.env.VITE_API_BASE ?? '';

function getToken(): string | null {
  return localStorage.getItem('token');
}

export function setToken(token: string): void {
  localStorage.setItem('token', token);
}

export function clearToken(): void {
  localStorage.removeItem('token');
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export class UnauthorizedError extends Error {
  constructor() {
    super('Unauthorized');
    this.name = 'UnauthorizedError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    throw new UnauthorizedError();
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Auth ──────────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${BASE}/web/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const b = await res.json();
      detail = b.detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export async function logout(): Promise<void> {
  await request('/web/api/auth/logout', { method: 'POST' });
}

export interface UserMe {
  id: number;
  username: string;
}

export async function getMe(): Promise<UserMe> {
  return request('/web/api/auth/me');
}

// ─── Gateway ───────────────────────────────────────────────────────────────────
export interface AdapterStatus {
  protocol?: string;
  running?: boolean;
  connections?: number;
  connected?: boolean;
  broker?: string;
}
export interface PipelineStatus {
  stages?: number;
  processed?: number;
  filtered?: number;
  errors?: number;
}
export interface MessageBusStatus {
  published?: number;
  delivered?: number;
  errors?: number;
  queue_size?: number;
  max_queue?: number;
  subscribers?: number;
}
export interface RegistryStatus {
  total?: number;
  online_count?: number;
}
export interface GeneralGatewayStatus {
  id?: string;
  name?: string;
  running?: boolean;
  start_time?: string;
}
export interface GatewayStatus {
  general?: GeneralGatewayStatus;
  devices?: RegistryStatus;
  bus?: MessageBusStatus;
  pipeline?: PipelineStatus;
  adapters?: Record<string, AdapterStatus>;
  uptime?: number;
}
export async function getGatewayStatus(): Promise<GatewayStatus> {
  return request('/web/api/gateway/status');
}

export interface GatewayConfig {
  general_config?: {
    general?: { id?: string; name?: string; storage?: string };
    devices?: { max_devices?: number; timeout_stale?: number; check_interval?: number };
    bus?: { max_queue?: number; timeout?: number };
    logger?: { dir?: string; debug?: boolean; level?: string };
  };
  adapter_configs?: Record<string, unknown>;
}
export async function getGatewayConfig(): Promise<GatewayConfig> {
  return request('/web/api/gateway/config');
}

// ─── Devices ───────────────────────────────────────────────────────────────────
export interface Device {
  device_id: string;
  name?: string;
  protocol?: string;
  registered_at?: string;
  last_seen?: string;
  metadata?: Record<string, unknown>;
}
export interface DeviceList {
  devices: Device[];
  total: number;
}
export async function getDevices(): Promise<DeviceList> {
  return request('/web/api/devices/');
}

export interface TelemetryRecord {
  device_id: string;
  payload: Record<string, unknown>;
  timestamp: string;
}
export interface DeviceTelemetry {
  device: Device;
  telemetry: { records: TelemetryRecord[]; total: number };
}
export async function getDevice(deviceId: string, limit = 20): Promise<DeviceTelemetry> {
  return request(
    `/web/api/devices/${encodeURIComponent(deviceId)}?limit=${limit}`
  );
}

export interface CommandRequest {
  command: string;
  params?: Record<string, unknown>;
  timeout?: number;
}
export interface CommandResponse {
  status: string;
  device_id: string;
  command: string;
}
export async function sendCommand(
  deviceId: string,
  body: CommandRequest
): Promise<CommandResponse> {
  return request(
    `/web/api/devices/${encodeURIComponent(deviceId)}/command`,
    { method: 'POST', body: JSON.stringify(body) }
  );
}

// ─── Logs ──────────────────────────────────────────────────────────────────────
export interface LogFile {
  filename: string;
  size_bytes: number;
  modified_at: string;
  is_active: boolean;
}
export interface LogFileList {
  files: LogFile[];
  total: number;
  logs_dir: string;
}
export interface LogLines {
  filename: string;
  lines: string[];
  total_lines: number;
  filtered_lines: number;
  level_filter: string | null;
  search_filter: string | null;
}
export async function getLogFiles(): Promise<LogFileList> {
  return request('/web/api/logs/list');
}
export async function getLogFile(
  filename: string,
  params: { level?: string; search?: string; lines?: number } = {}
): Promise<LogLines> {
  const q = new URLSearchParams();
  if (params.level) q.set('level', params.level);
  if (params.search) q.set('search', params.search);
  if (params.lines) q.set('lines', String(params.lines));
  const qs = q.toString() ? `?${q.toString()}` : '';
  return request(`/web/api/logs/${encodeURIComponent(filename)}${qs}`);
}
