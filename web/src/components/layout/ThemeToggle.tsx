import { useTheme } from '@/hooks/useTheme';

const ICON_PROPS = {
  'aria-hidden': true,
  focusable: false,
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const;

const SunIcon = () => (
  <svg {...ICON_PROPS}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
  </svg>
);

const MoonIcon = () => (
  <svg {...ICON_PROPS}>
    <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />
  </svg>
);

/**
 * CS-Y-09 — dark default, light on request. A toggle button: aria-pressed
 * reflects the light theme being active; the preference persists (useTheme).
 */
export const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === 'light';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-pressed={isLight}
      aria-label="Light theme"
      title={isLight ? 'Switch to dark theme' : 'Switch to light theme'}
      className="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted hover:bg-surface-2 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 motion-safe:transition-colors motion-safe:duration-120 motion-safe:ease-out"
    >
      {isLight ? <SunIcon /> : <MoonIcon />}
    </button>
  );
};
