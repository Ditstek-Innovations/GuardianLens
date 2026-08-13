import { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { Logo, ToastProvider } from '@/components/ui';
import { NAV_GROUP_ORDER, NAV_ITEMS } from '@/constants/roles';
import { useQueueQuery } from '@/features/review-queue';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils/cn';

import type { NavItem } from '@/constants/roles';

const MenuIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
  >
    <path d="M4 7h16M4 12h16M4 17h16" />
  </svg>
);

// ─── Queue depth — rendered by the shell so it is visible from EVERY screen
// (CS-SH-03, DP-4, CS-B-08). Shares the queue query cache; polling and
// pagination live in the feature hook. ─────────────────────────────────────

const QueueDepthChip = () => {
  const query = useQueueQuery();
  const depth = query.data?.pages[0]?.queue_depth;

  return (
    <span
      // CS-A-06 — depth changes announce politely; count in tabular figures.
      aria-live="polite"
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-brand-subtle px-3 py-1 text-xs font-medium text-brand-ink"
    >
      <span className="text-sm font-semibold tabular-nums">{depth ?? '—'}</span>
      <span>awaiting review</span>
    </span>
  );
};

// ─── Principal menu (CS-SH-09) ────────────────────────────────────────────

const PrincipalMenu = ({
  fullName,
  onSignOut,
}: {
  readonly fullName: string;
  readonly onSignOut: () => void;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Synchronising with the document click/key systems — legitimate effects.
  useEffect(() => {
    if (!isOpen) return undefined;
    const handlePointerDown = (event: PointerEvent): void => {
      if (containerRef.current !== null && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const initials = fullName
    .split(' ')
    .map((part) => part.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex items-center gap-2 rounded-control px-2 py-1.5 text-sm text-fg-muted hover:bg-surface-2 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 motion-safe:transition-colors motion-safe:duration-120 motion-safe:ease-out"
      >
        <span
          aria-hidden="true"
          className="flex h-7 w-7 items-center justify-center rounded-full bg-surface-3 text-xs font-semibold text-fg"
        >
          {initials}
        </span>
        <span className="hidden sm:inline">{fullName}</span>
      </button>
      {isOpen ? (
        <div className="absolute right-0 z-50 mt-1.5 w-48 rounded-card border border-border bg-surface-1 p-1 shadow-modal motion-safe:animate-fade-in">
          <p className="px-3 py-2 text-xs text-fg-muted">
            Signed in as <span className="font-medium text-fg">{fullName}</span>
          </p>
          <button
            type="button"
            onClick={onSignOut}
            className="block w-full rounded-control px-3 py-2 text-left text-sm text-fg hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-400"
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
};

// ─── Grouped navigation (CS-SH-02) ────────────────────────────────────────

const navLinkClass = ({ isActive }: { isActive: boolean }): string =>
  cn(
    'flex items-center gap-2 rounded-control border-l-2 px-3 py-2 text-sm font-medium',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2',
    'motion-safe:transition-colors motion-safe:duration-120 motion-safe:ease-out',
    isActive
      ? 'border-brand-400 bg-surface-2 text-brand-ink'
      : 'border-transparent text-fg-muted hover:bg-surface-2 hover:text-fg',
  );

const NavGroups = ({ items }: { readonly items: readonly NavItem[] }) => (
  <ul className="space-y-5">
    {NAV_GROUP_ORDER.map((group) => {
      const groupItems = items.filter((item) => item.group === group.id);
      if (groupItems.length === 0) return null;
      return (
        <li key={group.id}>
          <p className="px-3 pb-1.5 text-xs font-medium uppercase tracking-wide text-fg-faint">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {groupItems.map((item) => (
              <li key={item.path}>
                <NavLink to={item.path} className={navLinkClass}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </li>
      );
    })}
  </ul>
);

// ─── Mobile drawer (CS-SH-04) — traps focus, closes on Escape and on
// navigation; the depth indicator stays in the header, never inside. ──────

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled])';

const NavDrawer = ({
  items,
  onClose,
}: {
  readonly items: readonly NavItem[];
  readonly onClose: () => void;
}) => {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const panel = panelRef.current;
    if (panel === null) return undefined;
    panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusables = panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (first === undefined || last === undefined) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        type="button"
        aria-label="Close navigation"
        onClick={onClose}
        className="absolute inset-0 h-full w-full bg-overlay motion-safe:animate-fade-in"
      />
      <div
        ref={panelRef}
        className="absolute inset-y-0 left-0 flex w-64 flex-col gap-4 overflow-y-auto border-r border-border bg-surface-1 p-4 shadow-modal motion-safe:animate-drawer-in"
      >
        <nav aria-label="Primary">
          <NavGroups items={items} />
        </nav>
      </div>
    </div>
  );
};

// ─── The shell (CS-SH-01) — one header, one nav, one main ─────────────────

export const AppShell = () => {
  const { principal, signOut } = useAuth();
  const location = useLocation();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // CS-SH-04 — the drawer closes on navigation.
  useEffect(() => {
    setIsDrawerOpen(false);
  }, [location.pathname]);

  // Guarded by RequireAuth upstream; the null branch exists because the
  // context honestly types an unauthenticated state.
  if (principal === null) return null;

  const navItems = NAV_ITEMS.filter((item) =>
    item.roles.some((role) => principal.roles.includes(role)),
  );

  return (
    // CS-SH-07 — ToastProvider mounts THE toast region and announcer once,
    // for every screen inside the shell. Auth screens render outside it and
    // have no toast surface (CS-MSG-04).
    <ToastProvider>
    <div className="min-h-screen bg-bg">
      {/* CS-A-10 — skip link + landmarks. */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-control focus:bg-surface-1 focus:px-3 focus:py-2 focus:text-sm focus:text-fg focus:ring-2 focus:ring-brand-400"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-40 h-16 border-b border-border bg-surface-1">
        <div className="flex h-full items-center gap-3 px-4 sm:px-6">
          <button
            type="button"
            onClick={() => setIsDrawerOpen(true)}
            aria-label="Open navigation"
            aria-expanded={isDrawerOpen}
            className="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted hover:bg-surface-2 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 lg:hidden"
          >
            <MenuIcon />
          </button>
          <div className="flex items-center gap-2.5">
            <Logo />
            <span className="text-base font-semibold tracking-tight text-fg">Guardian Lens</span>
          </div>
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            {/* CS-SH-03 — depth is shell chrome, visible from every screen. */}
            <QueueDepthChip />
            <ThemeToggle />
            <PrincipalMenu fullName={principal.fullName} onSignOut={signOut} />
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-7xl">
        {/* CS-SH-04 — persistent sidebar at lg and above. */}
        <nav aria-label="Primary" className="hidden w-60 shrink-0 lg:block">
          <div className="sticky top-16 px-3 py-6">
            <NavGroups items={navItems} />
          </div>
        </nav>

        <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>

      {isDrawerOpen ? (
        <NavDrawer items={navItems} onClose={() => setIsDrawerOpen(false)} />
      ) : null}
    </div>
    </ToastProvider>
  );
};
