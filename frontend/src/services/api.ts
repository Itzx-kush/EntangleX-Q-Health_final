const base = (import.meta.env.VITE_API_BASE as string | undefined) || '/api';
let sessionToken = ''; // Memory only; never persisted to localStorage or logs.
export function setSessionToken(value: string) {sessionToken = value.trim(); window.dispatchEvent(new Event('qhealth-auth'));}
export function notifyDataChanged() {window.dispatchEvent(new Event('qhealth-data'));}

async function request(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  if (sessionToken) headers.set('Authorization', `Bearer ${sessionToken}`);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${base}${path}`, {...options, headers, credentials: 'omit', cache: 'no-store'});
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as {error?: {message?: string; request_id?: string}};
    const message = body.error?.message || `Request failed (${response.status}).`;
    throw new Error(body.error?.request_id ? `${message} Reference: ${body.error.request_id}` : message);
  }
  return response;
}
export const api = {
  async get<T>(path: string): Promise<T> {return (await request(path)).json() as Promise<T>;},
  async post<T>(path: string, body?: unknown): Promise<T> {return (await request(path, {method: 'POST', body: body === undefined ? undefined : JSON.stringify(body)})).json() as Promise<T>;},
  async upload<T>(path: string, body: FormData): Promise<T> {return (await request(path, {method: 'POST', body})).json() as Promise<T>;},
  async remove(path: string): Promise<void> {await request(path, {method: 'DELETE'});},
  async download(path: string, filename: string): Promise<void> {
    const response = await request(path);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a'); link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
