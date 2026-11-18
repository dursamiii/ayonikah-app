export type PlanStatus = 'todo' | 'in_progress' | 'done';
export type Plan = {
  id: number; title: string; category: string; status: PlanStatus;
  event_date: string | null; notes: string; image_url: string | null;
  created_at: string; updated_at: string;
};
export type PlanInput = Pick<Plan, 'title' | 'category' | 'status' | 'event_date' | 'notes' | 'image_url'>;
const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(`${baseUrl}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } }); }
  catch { throw new Error('Could not reach planner service. Check your connection and try again.'); }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { const body = await response.json(); message = body.detail ?? message; } catch { /* retain status message */ }
    throw new Error(typeof message === 'string' ? message : 'Please check your details and try again.');
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
function normalizePlan(plan: PlanInput): PlanInput {
  return { ...plan, event_date: plan.event_date || null, image_url: plan.image_url || null };
}

export const api = {
  list: () => request<Plan[]>('/api/plans'),
  create: (plan: PlanInput) => request<Plan>('/api/plans', { method: 'POST', body: JSON.stringify(normalizePlan(plan)) }),
  update: (id: number, plan: PlanInput) => request<Plan>(`/api/plans/${id}`, { method: 'PATCH', body: JSON.stringify(normalizePlan(plan)) }),
  remove: (id: number) => request<void>(`/api/plans/${id}`, { method: 'DELETE' }),
};
