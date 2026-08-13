// SCR-1c per FRONTEND_CODING_STANDARDS §23.3 — CS-AU-17: the token is read
// from the URL and never re-displayed; a bad link and a rejected token get
// the same single generic failure with a route back to SCR-1b.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { jsonResponse } from '@/test/factories';

import { ResetPasswordPage } from './ResetPasswordPage';

const GENERIC_FAILURE = 'The reset link is invalid or has expired.';
const TOKEN = 'tok-3f9a1c';

const renderAt = (url: string) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <ResetPasswordPage />
    </MemoryRouter>,
  );

const getPasswordInput = () => screen.getByLabelText(/new password/i, { selector: 'input' });

describe('ResetPasswordPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the generic failure immediately when the URL has no token (CS-AU-17)', () => {
    renderAt('/reset-password');

    expect(screen.getByRole('alert')).toHaveTextContent(GENERIC_FAILURE);
    expect(screen.getByRole('link', { name: /request a new reset link/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
    // No form to fill against a link that cannot work.
    expect(screen.queryByLabelText(/new password/i, { selector: 'input' })).toBeNull();
  });

  it('renders the same generic failure when the URL has a token but no email', () => {
    renderAt(`/reset-password?token=${TOKEN}`);
    expect(screen.getByRole('alert')).toHaveTextContent(GENERIC_FAILURE);
  });

  it('renders the exact generic copy on a 400 and never echoes the server detail or the token', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: unknown, _init?: RequestInit) =>
        jsonResponse({ error: { code: 'GL-4003', message: 'token expired 2 days ago' } }, 400),
      ),
    );
    const user = userEvent.setup();
    renderAt(`/reset-password?token=${TOKEN}&email=a@b.test`);

    await user.type(getPasswordInput(), 'a perfectly fine passphrase');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(GENERIC_FAILURE);
    expect(screen.queryByText(/expired 2 days ago/i)).toBeNull();
    // CS-AU-17 — the token never reaches the UI.
    expect(document.body.textContent).not.toContain(TOKEN);
    expect(screen.getByRole('link', { name: /request a new reset link/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
  });

  it('submits {email, token, new_password} and renders the success state on 200', async () => {
    const fetchMock = vi.fn(async (_input: unknown, _init?: RequestInit) =>
      jsonResponse({ ok: true }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderAt(`/reset-password?token=${TOKEN}&email=a@b.test`);

    await user.type(getPasswordInput(), 'a perfectly fine passphrase');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    expect(await screen.findByRole('status')).toHaveTextContent('Your password has been reset.');
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/api/v1/auth/password-reset');
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)) as unknown;
    expect(body).toEqual({
      email: 'a@b.test',
      token: TOKEN,
      new_password: 'a perfectly fine passphrase',
    });
  });

  it('keeps the policy inline: an 11-character password never leaves the client (CS-AU-15)', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderAt(`/reset-password?token=${TOKEN}&email=a@b.test`);

    await user.type(getPasswordInput(), 'elevenchars');
    await user.click(screen.getByRole('button', { name: /reset password/i }));

    expect(
      await screen.findByText('Password must be at least 12 characters.'),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
