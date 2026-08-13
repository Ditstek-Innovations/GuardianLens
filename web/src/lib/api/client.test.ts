import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { jsonResponse } from '@/test/factories';

import { apiClient } from './client';
import { ApiError } from './errors';
import { tokenStore } from './tokenStore';

const loginPayload = {
  access_token: 'access-2',
  refresh_token: 'refresh-2',
  token_type: 'bearer',
  expires_in: 900,
  user: { id: 'user-1', full_name: 'A Reviewer', roles: ['reviewer'] },
};

const headersOf = (init: RequestInit | undefined): Record<string, string> =>
  (init?.headers as Record<string, string> | undefined) ?? {};

describe('apiClient', () => {
  beforeEach(() => {
    tokenStore.set({ accessToken: 'access-1', refreshToken: 'refresh-1' });
  });

  afterEach(() => {
    tokenStore.clear();
    vi.unstubAllGlobals();
  });

  it('attaches the bearer token to every request', async () => {
    const fetchMock = vi.fn(async (_input: unknown, _init?: RequestInit) => jsonResponse({}));
    vi.stubGlobal('fetch', fetchMock);

    await apiClient.get('/api/v1/events');

    const firstCall = fetchMock.mock.calls[0];
    expect(firstCall).toBeDefined();
    expect(String(firstCall?.[0])).toContain('/api/v1/events');
    expect(headersOf(firstCall?.[1]).Authorization).toBe('Bearer access-1');
  });

  it('refreshes exactly once on a 401 and retries the original request with the new token', async () => {
    const fetchMock = vi.fn(async (input: unknown, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/v1/auth/refresh')) return jsonResponse(loginPayload);
      if (headersOf(init).Authorization === 'Bearer access-1') {
        return jsonResponse({ error: { code: 'GL-4011', message: 'token expired' } }, 401);
      }
      return jsonResponse({ items: [] });
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiClient.get<{ items: unknown[] }>('/api/v1/events');

    expect(result.items).toEqual([]);
    const refreshCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).includes('/api/v1/auth/refresh'),
    );
    expect(refreshCalls).toHaveLength(1);
    // Rotation stored the new pair (TRD §12.2).
    expect(tokenStore.get()?.accessToken).toBe('access-2');
    expect(tokenStore.get()?.refreshToken).toBe('refresh-2');
  });

  it('gives up after a failed refresh, clears the session and surfaces the 401', async () => {
    const fetchMock = vi.fn(async (input: unknown, _init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/api/v1/auth/refresh')) {
        return jsonResponse({ error: { code: 'GL-4012', message: 'refresh revoked' } }, 401);
      }
      return jsonResponse({ error: { code: 'GL-4011', message: 'token expired' } }, 401);
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(apiClient.get('/api/v1/events')).rejects.toMatchObject({ status: 401 });
    // The session ended — AuthProvider routes back to login (F-4).
    expect(tokenStore.get()).toBeNull();
    // Exactly one refresh attempt per failed request (CS-D-13).
    const refreshCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).includes('/api/v1/auth/refresh'),
    );
    expect(refreshCalls).toHaveLength(1);
  });

  it('maps the TRD §10.8 error envelope into a typed ApiError', async () => {
    const fetchMock = vi.fn(async (_input: unknown, _init?: RequestInit) =>
      jsonResponse(
        {
          error: {
            code: 'GL-4221',
            message: 'rejection_reason is required when decision is reject',
            field: 'rejection_reason',
            trace_id: 'trace-1',
          },
        },
        422,
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const failure = await apiClient.post('/api/v1/events/e1/decision', {}).catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    const apiError = failure as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.code).toBe('GL-4221');
    expect(apiError.field).toBe('rejection_reason');
    expect(apiError.traceId).toBe('trace-1');
  });
});
