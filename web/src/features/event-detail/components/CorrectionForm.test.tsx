import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { makeQueueEvent } from '@/test/factories';

import { CorrectionForm } from './CorrectionForm';

import type { EventDetail } from '@/lib/api/types';

const event: EventDetail = {
  ...makeQueueEvent(),
  rule_snapshot: {
    rule_type: 'found_bottle',
    confidence_threshold: 0.75,
    human_readable: 'Bottle detected',
    debounce_seconds: 30,
    dwell_seconds: null,
    detection_class: 'bottle',
  },
};

describe('CorrectionForm', () => {
  it('shows names and submits the selected UUID internally', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <CorrectionForm
        event={event}
        isSubmitting={false}
        isLoadingOptions={false}
        options={{
          zones: [
            { id: '11111111-1111-4111-8111-111111111111', name: 'Loading bay' },
            { id: '22222222-2222-4222-8222-222222222222', name: 'Main floor' },
          ],
          rules: [
            { id: '33333333-3333-4333-8333-333333333333', name: 'Bottle detected' },
          ],
        }}
        onSubmit={onSubmit}
        onCancel={() => undefined}
      />,
    );

    expect(screen.queryByText(/must be a UUID/i)).not.toBeInTheDocument();
    await user.selectOptions(
      screen.getByLabelText(/Corrected value/),
      '22222222-2222-4222-8222-222222222222',
    );
    await user.click(screen.getByRole('button', { name: 'Submit correction' }));

    expect(onSubmit).toHaveBeenCalledWith({
      field: 'zone_id',
      value: '22222222-2222-4222-8222-222222222222',
    });
  });
});
