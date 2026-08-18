import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DecisionBar } from './DecisionBar';

describe('DecisionBar', () => {
  it('keeps every decision control disabled until the evidence frame has loaded (ADR-013 / F-6)', async () => {
    const onIntent = vi.fn();
    render(<DecisionBar disabled isSubmitting={false} onIntent={onIntent} />);

    expect(screen.getByRole('button', { name: /accept/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /reject/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /correct/i })).toBeDisabled();
    expect(screen.getByText(/decisions enable once the evidence frame has loaded/i)).toBeInTheDocument();

    // Keyboard shortcuts must be inert while disabled.
    await userEvent.keyboard('a');
    await userEvent.keyboard('r');
    await userEvent.keyboard('c');
    expect(onIntent).not.toHaveBeenCalled();
  });

  it('fires accept, reject and correct intents from the A, R and C keys once enabled (NFR-ACC-01)', async () => {
    const onIntent = vi.fn();
    render(<DecisionBar disabled={false} isSubmitting={false} onIntent={onIntent} />);

    expect(screen.getByRole('button', { name: /accept/i })).toBeEnabled();

    await userEvent.keyboard('a');
    await userEvent.keyboard('r');
    await userEvent.keyboard('c');

    expect(onIntent).toHaveBeenNthCalledWith(1, 'accept');
    expect(onIntent).toHaveBeenNthCalledWith(2, 'reject');
    expect(onIntent).toHaveBeenNthCalledWith(3, 'correct');
  });

  it('fires intents from button clicks and exposes aria-keyshortcuts', async () => {
    const onIntent = vi.fn();
    render(<DecisionBar disabled={false} isSubmitting={false} onIntent={onIntent} />);

    const accept = screen.getByRole('button', { name: /accept/i });
    expect(accept).toHaveAttribute('aria-keyshortcuts', 'a');

    await userEvent.click(accept);
    expect(onIntent).toHaveBeenCalledWith('accept');
  });
});
