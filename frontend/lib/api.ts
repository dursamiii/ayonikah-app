export type PlanStatus = 'todo' | 'in_progress' | 'done';
export type Plan = {
  id: number;
  title: string;
  category: string;
  status: PlanStatus;
  event_date: string | null;
  notes: string;
  image_url: string | null;
  image_source?: 'none' | 'url' | 'upload';
  created_at: string;
  updated_at: string;
};
export type PlanInput = Pick<Plan, 'title' | 'category' | 'status' | 'event_date' | 'notes' | 'image_url'>;

export const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const timeoutMs = 15_000;

export function mediaUrl(url: string | null): string | null {
  if (!url) return null;
  try { return new URL(url, `${baseUrl}/`).toString(); }
  catch { return null; }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      signal: init?.signal ?? controller.signal,
      headers: { ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...init?.headers },
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw new Error('Request timed out. Please try again.');
    throw new Error('Could not reach planner service. Check your connection and try again.');
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      const envelope = body?.error;
      if (typeof envelope?.message === 'string') message = envelope.message;
      else if (typeof body?.detail === 'string') message = body.detail;
      else if (Array.isArray(body?.detail)) message = body.detail.map((entry: { msg?: string }) => entry.msg).filter(Boolean).join(' ');
    } catch { /* retain status message */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function normalizePlan(plan: PlanInput): PlanInput {
  return { ...plan, title: plan.title.trim(), category: plan.category.trim(), event_date: plan.event_date || null, image_url: plan.image_url?.trim() || null };
}

export const api = {
  list: () => request<Plan[]>('/api/plans'),
  create: (plan: PlanInput) => request<Plan>('/api/plans', { method: 'POST', body: JSON.stringify(normalizePlan(plan)) }),
  update: (id: number, plan: Partial<PlanInput>) => request<Plan>(`/api/plans/${id}`, { method: 'PATCH', body: JSON.stringify(Object.fromEntries(Object.entries(plan).map(([key, value]) => [key, key === 'title' || key === 'category' ? String(value).trim() : value === '' && (key === 'event_date' || key === 'image_url') ? null : value]))) }),
  remove: (id: number) => request<void>(`/api/plans/${id}`, { method: 'DELETE' }),
  uploadImage: (id: number, file: File) => { const body = new FormData(); body.append('file', file); return request<Plan>(`/api/plans/${id}/image`, { method: 'POST', body }); },
  removeImage: (id: number) => request<void>(`/api/plans/${id}/image`, { method: 'DELETE' }),
};
