import { useCallback, useEffect, useMemo, useState } from 'react';

import { isRole } from '@/constants/roles';
import { AuthContext } from '@/hooks/useAuth';
import { apiClient, restoreSession } from '@/lib/api/client';
import { tokenStore } from '@/lib/api/tokenStore';

import type { ReactNode } from 'react';
import type { Principal } from '@/hooks/useAuth';
import type { LoginResponse } from '@/lib/api/types';

export interface AuthProviderProps {
  readonly children: ReactNode;
}

const toPrincipal = (response: LoginResponse): Principal => ({
  id: response.user.id,
  fullName: response.user.full_name,
  // Unknown role strings from the wire are dropped, not crashed on.
  roles: response.user.roles.filter(isRole),
});

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [restoring, setRestoring] = useState<boolean>(
    () => tokenStore.persistedRefreshToken() !== null,
  );

  // A hard reload empties memory but not sessionStorage: rebuild the session
  // from the persisted refresh credential before guards decide anything.
  // restoreSession is once-per-page-load and StrictMode-safe (client.ts).
  useEffect(() => {
    void restoreSession().then((response) => {
      if (response !== null) setPrincipal(toPrincipal(response));
      setRestoring(false);
    });
  }, []);

  // When the refresh chain dies (rotation reuse, revocation, failed refresh)
  // the token store empties and the session ends — TRD §12.2, F-4. The user
  // is routed back to login by RequireAuth; any draft decision survives in
  // sessionStorage (TRD §7.3).
  useEffect(
    () =>
      tokenStore.subscribe(() => {
        if (tokenStore.get() === null) setPrincipal(null);
      }),
    [],
  );

  const signIn = useCallback(
    async (email: string, password: string, remember: boolean): Promise<void> => {
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', {
        email,
        password,
      });
      // CS-AU-19 — where the refresh credential persists is the user's
      // explicit choice, made here and kept across rotations.
      tokenStore.set(
        {
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
        },
        { remember },
      );
      setPrincipal(toPrincipal(response));
    },
    [],
  );

  const signOut = useCallback((): void => {
    // Best-effort server-side refresh-token revocation (TRD §10.2 logout).
    void apiClient.post('/api/v1/auth/logout').catch(() => undefined);
    tokenStore.clear();
  }, []);

  const value = useMemo(
    () => ({ principal, restoring, signIn, signOut }),
    [principal, restoring, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
