import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  it('reveals image on mouse hover and hides it on pointer leave', async () => {
    vi.mocked(api.list).mockResolvedValue([plan]);
    render(<Home />);
    const card = await screen.findByRole('article');
    fireEvent.pointerEnter(card, { pointerType: 'mouse' });
    expect(await screen.findByRole('img', { name: /reference image for book the garden/i })).toBeInTheDocument();
    fireEvent.pointerLeave(card, { pointerType: 'mouse' });
    await waitFor(() => expect(screen.queryByRole('img', { name: /reference image for book the garden/i })).not.toBeInTheDocument());
  });
  it('keeps button-open image visible after pointer leaves card', async () => {
    vi.mocked(api.list).mockResolvedValue([plan]);
    render(<Home />);
    const card = await screen.findByRole('article');
    fireEvent.click(screen.getByRole('button', { name: /view image/i }));
    fireEvent.pointerLeave(card, { pointerType: 'mouse' });
    expect(screen.getByRole('img', { name: /reference image for book the garden/i })).toBeInTheDocument();
  });
  it('shows fallback when image URL fails', async () => {
    vi.mocked(api.list).mockResolvedValue([plan]);
    render(<Home />);
    const card = await screen.findByRole('article');
    fireEvent.pointerEnter(card, { pointerType: 'mouse' });
    fireEvent.error(screen.getByRole('img', { name: /reference image for book the garden/i }));
    expect(await screen.findByText('Image unavailable')).toBeInTheDocument();
  });
  it('does not show hover preview for plan without image URL', async () => {
    vi.mocked(api.list).mockResolvedValue([{ ...plan, image_url: null }]);
    render(<Home />);
    const card = await screen.findByRole('article');
    fireEvent.pointerEnter(card, { pointerType: 'mouse' });
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
  it('offers image reveal by button independently of pointer hover', async () => {
    vi.mocked(api.list).mockResolvedValue([plan]);
    const user = userEvent.setup();
    render(<Home />);
    const card = await screen.findByRole('article');
    fireEvent.pointerEnter(card, { pointerType: 'mouse' });
    fireEvent.pointerLeave(card, { pointerType: 'mouse' });
    expect(screen.queryByRole('img', { name: /reference image for book the garden/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /view image/i }));
    expect(await screen.findByRole('img', { name: /reference image for book the garden/i })).toBeInTheDocument();
    fireEvent.pointerEnter(card, { pointerType: 'mouse' });
    fireEvent.pointerLeave(card, { pointerType: 'mouse' });
    expect(screen.getByRole('img', { name: /reference image for book the garden/i })).toBeInTheDocument();
  });
  it('shows graceful fallback when reference image fails to load', async () => {
    vi.mocked(api.list).mockResolvedValue([plan]);
    render(<Home />);
    const card = await screen.findByRole('article');
    fireEvent.click(screen.getByRole('button', { name: /view image/i }));
    fireEvent.error(await screen.findByRole('img', { name: /reference image for book the garden/i }));
    expect(await screen.findByRole('status')).toHaveTextContent('Image unavailable');
    expect(card).toBeInTheDocument();
  });
});
