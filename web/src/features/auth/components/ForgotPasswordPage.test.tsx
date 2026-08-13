// SCR-1b per FRONTEND_CODING_STANDARDS §23.3 — CS-AU-17: one acceptance
// line, account or no account, whatever the 202 payload says.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { jsonResponse } from '@/test/factories';

import { ForgotPasswordPage } from './ForgotPasswordPage';

const ACCEPTANCE = 'If that address has an account, a reset link has been sent.';

const renderPage = () => render(<ForgotPasswordPage />, { wrapper: MemoryRouter });

describe('ForgotPasswordPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each([
    // A payload that names the account — the UI must not echo it.
    { status: 'accepted', message: 'No account exists for that address' },
    {},
  ])('always renders the same acceptance on 202 (CS-AU-17) %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(payload, 202)));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/email/i), 'someone@example.test');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    expect(await screen.findByRole('status')).toHaveTextContent(ACCEPTANCE);
    expect(screen.queryByText(/no account exists/i)).toBeNull();
    // The form is done — one field, one outcome, and the way back (CS-AU-18).
    expect(screen.queryByLabelText(/email/i)).toBeNull();
    expect(screen.getByRole('link', { name: /back to sign in/i })).toHaveAttribute(
      'href',
      '/login',
    );
  });
});
