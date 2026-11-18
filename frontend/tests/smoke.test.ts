import { describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';

describe('planner API contract', () => {
  it('calls item collection and item routes', async () => {
    const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response('[]', { status: 200 })).mockResolvedValueOnce(new Response('{"id":1}', { status: 201 })).mockResolvedValueOnce(new Response('{"id":1}', { status: 200 })).mockResolvedValueOnce(new Response(null, { status: 204 }));
    await api.list();
    await api.create({ title: 'Venue', category: 'venue', status: 'todo', event_date: '', notes: '', image_url: '' });
    await api.update(1, { title: 'Venue', category: 'venue', status: 'done', event_date: '', notes: '', image_url: '' });
    await api.remove(1);
    expect(fetcher.mock.calls.map(([url]) => String(url))).toEqual([
      'http://localhost:8000/api/plans', 'http://localhost:8000/api/plans',
      'http://localhost:8000/api/plans/1', 'http://localhost:8000/api/plans/1',
    ]);
    fetcher.mockRestore();
  });

  it('surfaces API validation errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response('{"detail":"Invalid plan"}', { status: 422 }));
    await expect(api.list()).rejects.toThrow('Invalid plan');
    vi.restoreAllMocks();
  });
});
