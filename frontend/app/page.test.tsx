import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Home from './page';
import { api, type Plan } from '@/lib/api';

vi.mock('@/lib/api', () => ({ api: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() } }));
const plan: Plan = { id: 1, title: 'Book the garden', category: 'Venue', status: 'todo', event_date: null, notes: '', image_url: 'https://example.com/garden.jpg', created_at: '', updated_at: '' };
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe('planner', () => {
  it('shows loading state then empty state', async () => {
    vi.mocked(api.list).mockResolvedValue([]);
    render(<Home />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading your plans');
    expect(await screen.findByText('Your first plan starts here.')).toBeInTheDocument();
  });
  it('creates plan through keyboard-accessible form', async () => {
    vi.mocked(api.list).mockResolvedValue([]);
    vi.mocked(api.create).mockResolvedValue(plan);
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText('Your first plan starts here.');
    await user.click(screen.getByRole('button', { name: /add first plan/i }));
    await user.type(screen.getByLabelText(/title/i), plan.title);
    await user.click(screen.getByRole('button', { name: 'Add plan' }));
    expect(await screen.findByText(plan.title)).toBeInTheDocument();
    expect(api.create).toHaveBeenCalledOnce();
  });
  it('offers image reveal by button for non-hover input', async () => {
    vi.mocked(api.list).mockResolvedValue([plan]);
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText(plan.title);
    await user.click(screen.getByRole('button', { name: /view image/i }));
    await waitFor(() => expect(screen.getByRole('img', { name: /reference image for book the garden/i })).toBeInTheDocument());
  });
});
