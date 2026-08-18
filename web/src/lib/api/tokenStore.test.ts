// CS-AU-19 — where the refresh credential persists is the user's explicit
// choice: sessionStorage by default, localStorage only behind the opt-in.
// Exactly one store ever holds it; clearing wipes both.
import { afterEach, describe, expect, it } from 'vitest';

import { REFRESH_TOKEN_STORAGE_KEY } from '@/constants/storage';

import { tokenStore } from './tokenStore';

const TOKENS = { accessToken: 'access-1', refreshToken: 'refresh-1' };

afterEach(() => {
  tokenStore.clear();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe('tokenStore persistence modes', () => {
  it('defaults to sessionStorage: the credential dies with the tab', () => {
    tokenStore.set(TOKENS, { remember: false });
    expect(window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('refresh-1');
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('opt-in moves the credential to localStorage and keeps the mode across rotations', () => {
    tokenStore.set(TOKENS, { remember: true });
    // A rotation call carries no remember option — the chosen mode holds.
    tokenStore.set({ accessToken: 'access-2', refreshToken: 'refresh-2' });
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('refresh-2');
    expect(window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull();
  });

  it('signing in WITHOUT the opt-in clears any remembered credential from a prior session', () => {
    tokenStore.set(TOKENS, { remember: true });
    tokenStore.set({ accessToken: 'access-3', refreshToken: 'refresh-3' }, { remember: false });
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('refresh-3');
  });

  it('clear() wipes both stores', () => {
    tokenStore.set(TOKENS, { remember: true });
    tokenStore.clear();
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBeNull();
    expect(tokenStore.get()).toBeNull();
  });

  it('restore prefers the remembered credential and re-arms the remembered mode', () => {
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, 'remembered-token');
    expect(tokenStore.persistedRefreshToken()).toBe('remembered-token');
    // The next rotation must keep writing where the credential was found.
    tokenStore.set({ accessToken: 'access-4', refreshToken: 'refresh-4' });
    expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('refresh-4');
  });
});
