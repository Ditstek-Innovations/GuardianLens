// §12.1 "Brand mark" — one drawing, three placements: shell header, auth
// identity panel, favicon. These tests pin the single-component rule and
// the byte-for-byte favicon mirror.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AppShell } from '@/components/layout/AppShell';
import { AuthLayout } from '@/features/auth/components/AuthLayout';
import { AuthContext } from '@/hooks/useAuth';
import { jsonResponse, makeQueuePage } from '@/test/factories';

import { LOGO_IRIS, LOGO_PUPIL, LOGO_SHIELD_PATH } from './Logo';

const shieldsIn = (container: HTMLElement): number =>
  container.querySelectorAll(`path[d="${LOGO_SHIELD_PATH}"]`).length;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Logo placements', () => {
  it('renders the one brand mark in the shell header', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(makeQueuePage([], 0))));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <AuthContext.Provider
        value={{
          principal: { id: 'user-1', fullName: 'A. Reviewer', roles: ['reviewer'] },
          restoring: false,
          signIn: async () => undefined,
          signOut: () => undefined,
        }}
      >
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/']}>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<p>screen content</p>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    expect(await screen.findByText('screen content')).toBeInTheDocument();
    // Exactly one drawing of the mark, inside the banner landmark.
    expect(shieldsIn(container)).toBe(1);
    expect(screen.getByRole('banner').querySelector(`path[d="${LOGO_SHIELD_PATH}"]`)).not.toBeNull();
  });

  it('renders the one brand mark in the auth identity panel', () => {
    const { container } = render(
      <MemoryRouter>
        <AuthLayout title="Sign in">
          <p>form goes here</p>
        </AuthLayout>
      </MemoryRouter>,
    );
    expect(shieldsIn(container)).toBe(1);
  });

  it('mirrors the mark geometry byte-for-byte in public/favicon.svg with the dark tile', () => {
    const favicon = readFileSync(join(process.cwd(), 'public', 'favicon.svg'), 'utf8');

    // Byte-for-byte geometry: shield path, iris and pupil as drawn in Logo.tsx.
    expect(favicon).toContain(`d="${LOGO_SHIELD_PATH}"`);
    expect(favicon).toContain(`cx="${LOGO_IRIS.cx}" cy="${LOGO_IRIS.cy}" r="${LOGO_IRIS.r}"`);
    expect(favicon).toContain(`r="${LOGO_PUPIL.r}"`);
    // Dark-tile variant: bg tile + brand-400 mark, so the tab reads on
    // light AND dark browser chrome.
    expect(favicon).toContain('#0B0F14');
    expect(favicon).toContain('#22D3EE');
  });

  it('wires the favicon into index.html', () => {
    const html = readFileSync(join(process.cwd(), 'index.html'), 'utf8');
    expect(html).toContain('rel="icon"');
    expect(html).toContain('href="/favicon.svg"');
    expect(html).toContain('type="image/svg+xml"');
  });
});
