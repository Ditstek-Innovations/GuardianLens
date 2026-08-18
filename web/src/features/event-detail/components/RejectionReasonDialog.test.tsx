import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RejectionReasonDialog } from './RejectionReasonDialog';

const Harness = ({ onSubmit }: { onSubmit: (reason: string) => void }) => {
  const [draft, setDraft] = useState('');
  return (
    <RejectionReasonDialog
      draft={draft}
      onDraftChange={setDraft}
      isSubmitting={false}
      onSubmit={onSubmit}
      onCancel={() => undefined}
    />
  );
};

describe('RejectionReasonDialog', () => {
  it('refuses to submit without a reason (FR-043 — mandatory, not nudged)', async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole('button', { name: /reject candidate/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/a rejection reason is required/i);
  });

  it('refuses a whitespace-only reason', async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/rejection reason/i), '   ');
    await userEvent.click(screen.getByRole('button', { name: /reject candidate/i }));

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits the trimmed reason when one is given', async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);

    await userEvent.type(
      screen.getByLabelText(/rejection reason/i),
      'Person was carrying the helmet, not required in transit',
    );
    await userEvent.click(screen.getByRole('button', { name: /reject candidate/i }));

    expect(onSubmit).toHaveBeenCalledWith('Person was carrying the helmet, not required in transit');
  });
});
