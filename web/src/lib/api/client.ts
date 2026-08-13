import { env } from '@/lib/env';

import { toApiError } from './errors';
import { tokenStore } from './tokenStore';

import type { LoginResponse } from './types';

/** CS-D-01 — fetch is called in exactly this file. */

export type QueryParams = Record<string, string | number | boolean | undefined>;

export interface RequestOptions {
  query?: QueryParams | undefined;
  signal?: AbortSignal | undefined;
}

interface InternalRequest {
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: QueryParams | undefined;
  signal?: AbortSignal | undefined;
}

const buildUrl = (path: string, query?: QueryParams): string => {
  const url = new URL(`${env.apiUrl}${path}`);
  if (query !== undefined) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
};

let refreshInFlight: Promise<LoginResponse | null> | null = null;

const performRefresh = async (): Promise<LoginResponse | null> => {
  // After a hard reload memory is empty but the refresh credential survives
  // in sessionStorage — fall back to it so the session can be rebuilt.
  const refreshToken = tokenStore.get()?.refreshToken ?? tokenStore.persistedRefreshToken();
  if (refreshToken === null) return null;
  try {
    // ASSUMPTION A-1 — refresh takes { refresh_token } and returns the login
    // payload shape (TRD §10.2 says only "standard refresh-token rotation").
    const response = await fetch(buildUrl('/api/v1/auth/refresh'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      tokenStore.clear();
      return null;
    }
    const data = (await response.json()) as LoginResponse;
    tokenStore.set({ accessToken: data.access_token, refreshToken: data.refresh_token });
    return data;
  } catch {
    tokenStore.clear();
    return null;
  }
};

/** CS-D-13 — refresh is single-flight and attempted at most once per failed request. */
const refreshTokens = (): Promise<LoginResponse | null> => {
  if (refreshInFlight === null) {
    refreshInFlight = performRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
};

let restoreOutcome: Promise<LoginResponse | null> | null = null;

/**
 * CS-AU-07 — session restore after a hard reload, owned by the client like
 * every other refresh. Rotates the persisted refresh credential and returns
 * the login payload for AuthProvider to derive the principal, or null when
 * there is nothing to restore or the chain is dead. The outcome is cached:
 * restore happens once per page load, so repeat calls (React StrictMode
 * double-mount) must not spend a second rotation of the same token.
 */
export const restoreSession = (): Promise<LoginResponse | null> => {
  restoreOutcome ??=
    tokenStore.persistedRefreshToken() === null ? Promise.resolve(null) : refreshTokens();
  return restoreOutcome;
};

const execute = async (
  path: string,
  request: InternalRequest,
  allowRefresh: boolean,
): Promise<Response> => {
  const tokens = tokenStore.get();
  const headers: Record<string, string> = {};
  if (request.body !== undefined) headers['Content-Type'] = 'application/json';
  if (tokens !== null) headers.Authorization = `Bearer ${tokens.accessToken}`;

  const response = await fetch(buildUrl(path, request.query), {
    method: request.method,
    headers,
    ...(request.body !== undefined ? { body: JSON.stringify(request.body) } : {}),
    ...(request.signal !== undefined ? { signal: request.signal } : {}),
  });

  if (response.status === 401 && allowRefresh && !path.startsWith('/api/v1/auth/')) {
    const refreshed = await refreshTokens();
    if (refreshed !== null) return execute(path, request, false);
  }
  return response;
};

const requestJson = async <T>(path: string, request: InternalRequest): Promise<T> => {
  const response = await execute(path, request, true);
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) {
    // No content — callers of void endpoints type T as undefined/unknown.
    return undefined as T;
  }
  // Boundary assertion stands in for a generated runtime schema (CS-G-10);
  // see lib/api/types.ts header for the replacement plan.
  return (await response.json()) as T;
};

export const apiClient = {
  get: <T>(path: string, options: RequestOptions = {}): Promise<T> =>
    requestJson<T>(path, { method: 'GET', ...options }),
  post: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    requestJson<T>(path, { method: 'POST', body, ...options }),
  patch: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    requestJson<T>(path, { method: 'PATCH', body, ...options }),
  /** Evidence frames and exports arrive as authenticated blobs (bearer header). */
  getBlob: async (path: string, options: RequestOptions = {}): Promise<Blob> => {
    const response = await execute(path, { method: 'GET', ...options }, true);
    if (!response.ok) throw await toApiError(response);
    return response.blob();
  },
};
