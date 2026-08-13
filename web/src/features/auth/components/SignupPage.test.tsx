// SCR-1a per FRONTEND_CODING_STANDARDS §23.3 — CS-AU-16: one generic
// acceptance regardless of the 202 payload, and CS-AU-15's policy enforced
// client-side before any request leaves.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { jsonResponse } from '@/test/factories';

import { SignupPage } from './SignupPage';

const renderPage = () => render(<SignupPage />, { wrapper: MemoryRouter });

const fillForm = async (
  user: ReturnType<typeof userEvent.setup>,
  password: string,
): Promise<void> => {
  await user.type(screen.getByLabelText(/full name/i), 'A Reviewer');
  await user.type(screen.getByLabelText(/email/i), 'a@b.test');
  await user.type(screen.getByLabelText(/site code/i), 'SITE-42');
  await user.type(screen.getByLabelText(/^password/i, { selector: 'input' }), password);
  await user.click(screen.getByRole('button', { name: /request an account/i }));
};

describe('SignupPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each([
    // A leaky payload the UI must never surface (CS-AU-16).
    { status: 'accepted', message: 'An account already exists for this address' },
    // A payload with nothing useful in it at all.
    {},
  ])('renders the one generic acceptance on 202 regardless of payload (CS-AU-16) %#', async (payload) => {
    const fetchMock = vi.fn(async (_input: unknown, _init?: RequestInit) =>
      jsonResponse(payload, 202),
    );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderPage();

    await fillForm(user, 'a perfectly fine passphrase');

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Your account has been requested.',
    );
    expect(screen.getByText(/a site administrator assigns access/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to sign in/i })).toHaveAttribute(
      'href',
      '/login',
    );
    // Never a word from the payload, never a hint about what already existed.
    expect(screen.queryByText(/already exists/i)).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)) as unknown;
    expect(body).toEqual({
      full_name: 'A Reviewer',
      email: 'a@b.test',
      password: 'a perfectly fine passphrase',
      site_code: 'SITE-42',
    });
  });

  it('rejects an 11-character password inline and never calls the API (CS-AU-15)', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderPage();

    await fillForm(user, 'elevenchars'); // 11 characters — one short of policy

    expect(
      await screen.findByText('Password must be at least 12 characters.'),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    // CS-FM-06 — the failed submit never clears what was typed.
    expect(screen.getByLabelText(/^password/i, { selector: 'input' })).toHaveValue('elevenchars');
  });

  it('states the password policy in the hint before any failure (CS-AU-15)', () => {
    renderPage();
    expect(screen.getByText(/12 to 128 characters\. no other requirements/i)).toBeInTheDocument();
    expect(screen.getByText(/provided by your site administrator/i)).toBeInTheDocument();
  });
});
