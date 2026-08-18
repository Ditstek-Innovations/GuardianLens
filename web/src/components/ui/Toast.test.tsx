// CS-MSG-03 — the toast lifecycle contract: success auto-dismisses (5 s,
// pausable on hover/focus), failure persists until dismissed, keyboard
// dismissal, max 3 stacked with the oldest collapsing, and the correct
// announcement roles (success polite/status, failure assertive/alert).
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TOAST_AUTO_DISMISS_MS } from '@/constants/time';
import { useToast } from '@/hooks/useToast';

import { ToastProvider } from './Toast';

import type { ToastInput } from '@/hooks/useToast';

const Trigger = ({ toasts }: { readonly toasts: readonly ToastInput[] }) => {
  const { showToast } = useToast();
  return (
    <button
      type="button"
      onClick={() => {
        toasts.forEach(showToast);
      }}
    >
      fire
    </button>
  );
};

const renderWithToasts = (toasts: readonly ToastInput[]) => {
  render(
    <ToastProvider>
      <Trigger toasts={toasts} />
    </ToastProvider>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'fire' }));
};

const advance = (ms: number): void => {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('ToastProvider', () => {
  it('auto-dismisses a success toast after 5 s and announces it politely', () => {
    renderWithToasts([{ tone: 'success', message: 'Recorded — consequence stated.' }]);

    const toast = screen.getByRole('status');
    expect(toast).toHaveTextContent('Recorded — consequence stated.');

    advance(TOAST_AUTO_DISMISS_MS - 1);
    expect(screen.getByRole('status')).toBeInTheDocument();
    advance(1);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('pauses the auto-dismiss timer while hovered and resumes on leave', () => {
    renderWithToasts([{ tone: 'success', message: 'Recorded — consequence stated.' }]);

    fireEvent.mouseEnter(screen.getByRole('status'));
    advance(TOAST_AUTO_DISMISS_MS * 3);
    expect(screen.getByRole('status')).toBeInTheDocument();

    fireEvent.mouseLeave(screen.getByRole('status'));
    advance(TOAST_AUTO_DISMISS_MS);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('pauses the auto-dismiss timer while focus is inside the toast', () => {
    renderWithToasts([{ tone: 'success', message: 'Recorded — consequence stated.' }]);

    const dismissButton = screen.getByRole('button', { name: 'Dismiss notification' });
    fireEvent.focus(dismissButton);
    advance(TOAST_AUTO_DISMISS_MS * 3);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('keeps a failure toast until it is dismissed, announced assertively', () => {
    renderWithToasts([{ tone: 'failure', message: 'Not recorded. Check the connection.' }]);

    advance(TOAST_AUTO_DISMISS_MS * 10);
    const toast = screen.getByRole('alert');
    expect(toast).toHaveTextContent('Not recorded. Check the connection.');

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('dismisses on Escape when the toast has focus (CS-A keyboard dismissal)', () => {
    renderWithToasts([{ tone: 'failure', message: 'Not recorded. Check the connection.' }]);

    const dismissButton = screen.getByRole('button', { name: 'Dismiss notification' });
    dismissButton.focus();
    fireEvent.keyDown(dismissButton, { key: 'Escape' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('stacks at most 3 toasts — the oldest collapses', () => {
    renderWithToasts([
      { tone: 'failure', message: 'first outcome' },
      { tone: 'failure', message: 'second outcome' },
      { tone: 'failure', message: 'third outcome' },
      { tone: 'failure', message: 'fourth outcome' },
    ]);

    expect(screen.queryByText('first outcome')).not.toBeInTheDocument();
    expect(screen.getByText('second outcome')).toBeInTheDocument();
    expect(screen.getByText('third outcome')).toBeInTheDocument();
    expect(screen.getByText('fourth outcome')).toBeInTheDocument();
  });
});
