import { createContext, useContext } from 'react';

import type { Role } from '@/constants/roles';

export interface Principal {
  readonly id: string;
  readonly fullName: string;
  readonly roles: readonly Role[];
}

export interface AuthContextValue {
  readonly principal: Principal | null;
  /** True while a reload-surviving session is being rebuilt from the
   * persisted refresh credential — guards must wait, not redirect. */
  readonly restoring: boolean;
  readonly signIn: (email: string, password: string, remember: boolean) => Promise<void>;
  readonly signOut: () => void;
}

/** TRD §7.3 — auth state lives in React Context; no global store (CS-S-07). */
export const AuthContext = createContext<AuthContextValue | null>(null);

export const useAuth = (): AuthContextValue => {
  const value = useContext(AuthContext);
  if (value === null) throw new Error('useAuth must be used within AuthProvider');
  return value;
};
