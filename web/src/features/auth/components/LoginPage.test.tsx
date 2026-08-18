// SCR-1 behaviour per FRONTEND_CODING_STANDARDS §23.3 — the rules that are
// cheapest to lose in a refactor: the exact 401 copy, the distinct 429, the
// open-redirect guard, and the CS-AU-18 link set (auth siblings only, no
// social sign-in).
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';

import { LoginPage } from './LoginPage';

const signIn = vi.fn();
const navigate = vi.fn();
let locationState: unknown = null;

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ principal: null, signIn }),
}));
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
  useLocation: () => ({ state: locationState, pathname: '/login' }),
}));

const renderPage = () => render(<LoginPage />, { wrapper: MemoryRouter });

const submit = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.type(screen.getByLabelText(/email/i), 'a@b.test');
  // selector: the PasswordInput toggle also carries "password" in its
  // accessible name ("Show password"); the field is the input.
  await user.type(screen.getByLabelText(/password/i, { selector: 'input' }), 'pw');
  await user.click(screen.getByRole('button', { name: /sign in/i }));
};

describe('LoginPage', () => {
  beforeEach(() => {
    signIn.mockReset();
    navigate.mockReset();
    locationState = null;
  });

  it('renders the exact generic message on a credential failure (CS-AU-04)', async () => {
    signIn.mockRejectedValueOnce(new ApiError(401, 'unauthorised'));
    const user = userEvent.setup();
    renderPage();
    await submit(user);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Email or password is incorrect.');
    // The alert receives focus so a failed submit is announced (CS-FM-04).
    await waitFor(() => expect(alert).toHaveFocus());
  });

  it('renders a distinct honest message on 429, never the credential copy (CS-AU-05)', async () => {
    signIn.mockRejectedValueOnce(new ApiError(429, 'rate limited'));
    const user = userEvent.setup();
    renderPage();
    await submit(user);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/too many sign-in attempts/i);
    expect(alert).not.toHaveTextContent(/incorrect/i);
    expect(signIn).toHaveBeenCalledTimes(1); // never auto-retried
  });

  it('refuses an external redirect target (CS-AU-08)', async () => {
    signIn.mockResolvedValueOnce(undefined);
    locationState = { from: '//evil.example/queue' };
    const user = userEvent.setup();
    renderPage();
    await submit(user);

    // The guard falls back to the queue — the home route (CS-AU-08).
    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/queue', expect.anything()),
    );
  });

  it('links to exactly its auth siblings, and offers no social sign-in (CS-AU-10, CS-AU-18)', () => {
    renderPage();

    // Amended CS-AU-10 (v1.4): sign-up and forgot-password EXIST as links —
    // these two, and nothing else.
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(2);
    expect(screen.getByRole('link', { name: /create an account/i })).toHaveAttribute(
      'href',
      '/signup',
    );
    expect(screen.getByRole('link', { name: /forgot password/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
    // The 1.3 prohibition survives for social sign-in only.
    expect(screen.queryByText(/google|microsoft|github|facebook|sso|single sign/i)).toBeNull();
  });
});
