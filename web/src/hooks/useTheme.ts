import { useCallback, useState } from 'react';

import { THEME_STORAGE_KEY } from '@/constants/storage';

export type Theme = 'dark' | 'light';

const LIGHT_CLASS = 'light';

const readTheme = (): Theme =>
  document.documentElement.classList.contains(LIGHT_CLASS) ? 'light' : 'dark';

/**
 * CS-Y-09 — dark is the default theme; light is the `light` class on <html>.
 * The class is applied pre-hydration by the inline snippet in index.html, so
 * this hook only mirrors and toggles it. The preference persists across
 * sessions (device preference, not session state — see constants/storage.ts).
 */
export const useTheme = (): { readonly theme: Theme; readonly toggleTheme: () => void } => {
  const [theme, setTheme] = useState<Theme>(readTheme);

  const toggleTheme = useCallback((): void => {
    setTheme((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark';
      document.documentElement.classList.toggle(LIGHT_CLASS, next === 'light');
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch {
        // Storage unavailable — the toggle still works for this session.
      }
      return next;
    });
  }, []);

  return { theme, toggleTheme };
};
