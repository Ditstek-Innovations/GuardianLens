import { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { Button, Logo, Modal, ToastProvider } from '@/components/ui';
import { NAV_GROUP_ORDER, NAV_ITEMS } from '@/constants/navigation';
import { ROUTES } from '@/constants/routes';
import { useQueueQuery } from '@/features/review-queue';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils/cn';

import type { ReactElement } from 'react';
import type { NavIconName, NavItem } from '@/constants/navigation';

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

// ─── Nav icons — §12.1 inline SVG, stroke = currentColor so each rides its
// link's state colour. One drawing per NavIconName; the names live with the
// nav declaration (CS-SH-02), the geometry lives here with the shell. ───────

const navIconProps = {
  'aria-hidden': true,
  focusable: false,
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  className: 'shrink-0',
} as const;

const QueueIcon = () => (
  <svg {...navIconProps}>
    <path d="M5.5 5h13l2.5 8v5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-5l2.5-8Z" />
    <path d="M3 13h5l1.5 2.5h5L16 13h5" />
  </svg>
);

const ReportsIcon = () => (
  <svg {...navIconProps}>
    <path d="M4 4v15a1 1 0 0 0 1 1h15" />
    <path d="M8.5 16v-4" />
    <path d="M13 16V8" />
    <path d="M17.5 16v-6.5" />
  </svg>
);

const ConfigurationIcon = () => (
  <svg {...navIconProps}>
    <path d="M4 7.5h9" />
    <circle cx="15.5" cy="7.5" r="2.5" />
    <path d="M18 7.5h2" />
    <path d="M4 16.5h2" />
    <circle cx="8.5" cy="16.5" r="2.5" />
    <path d="M11 16.5h9" />
  </svg>
);

const AuditIcon = () => (
  <svg {...navIconProps}>
    <path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
    <path d="M14 3v4h4" />
    <path d="M9.5 12.5h5" />
    <path d="M9.5 16h5" />
  </svg>
);

const HistoryIcon = () => (
  <svg {...navIconProps}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </svg>
);

const NAV_ICONS: Record<NavIconName, () => ReactElement> = {
  queue: QueueIcon,
  history: HistoryIcon,
  reports: ReportsIcon,
  configuration: ConfigurationIcon,
  audit: AuditIcon,
};

// ─── Queue depth — rendered by the shell so it is visible from EVERY screen
// (CS-SH-03, DP-4, CS-B-08). One shared subscription in AppShell feeds this
// chip and the rail badge; polling and pagination live in the feature hook. ─

const QueueDepthChip = ({ depth }: { readonly depth: number | undefined }) => (
  <span
    // CS-A-06 — depth changes announce politely; count in tabular figures.
    aria-live="polite"
    className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-brand-subtle px-3 py-1 text-xs font-medium text-brand-ink"
  >
    <span className="text-sm font-semibold tabular-nums">{depth ?? '—'}</span>
    <span>awaiting review</span>
  </span>
);

// ─── Principal menu (CS-SH-09) ────────────────────────────────────────────

/**
 * Sign-out is confirmed, not instant: it ends the session and clears the
 * query cache and any session drafts (CS-AU-09) — worth one explicit step,
 * stated in plain words. It renders outside the menu popover so closing
 * the menu does not unmount it.
 */
const SignOutDialog = ({
  onConfirm,
  onCancel,
}: {
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => (
  <Modal title="Sign out" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        Your session on this device ends now. Any draft decision saved on this device is cleared
        with it.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm}>
          Sign out
        </Button>
      </div>
    </div>
  </Modal>
);

const PrincipalMenu = ({
  fullName,
  onSignOut,
}: {
  readonly fullName: string;
  readonly onSignOut: () => void;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isConfirmingSignOut, setIsConfirmingSignOut] = useState(false);
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
            onClick={() => {
              setIsOpen(false);
              setIsConfirmingSignOut(true);
            }}
            className="block w-full rounded-control px-3 py-2 text-left text-sm text-fg hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-400"
          >
            Sign out
          </button>
        </div>
      ) : null}
      {isConfirmingSignOut ? (
        <SignOutDialog
          onConfirm={onSignOut}
          onCancel={() => setIsConfirmingSignOut(false)}
        />
      ) : null}
    </div>
  );
};

// ─── Grouped navigation (CS-SH-02) ────────────────────────────────────────

const navLinkClass = ({ isActive }: { isActive: boolean }): string =>
  cn(
    'group flex items-center gap-2.5 rounded-control px-2.5 py-2 text-sm font-medium',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2',
    'motion-safe:transition-colors motion-safe:duration-120 motion-safe:ease-out',
    isActive ? 'bg-brand-subtle text-brand-ink' : 'text-fg-muted hover:bg-surface-2 hover:text-fg',
  );

const NavGroups = ({
  items,
  queueDepth,
}: {
  readonly items: readonly NavItem[];
  readonly queueDepth: number | undefined;
}) => (
  <ul className="space-y-5">
    {NAV_GROUP_ORDER.map((group) => {
      const groupItems = items.filter((item) => item.group === group.id);
      if (groupItems.length === 0) return null;
      return (
        <li key={group.id}>
          <p className="px-2.5 pb-1.5 text-xs font-semibold uppercase tracking-wider text-fg-faint">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {groupItems.map((item) => {
              const Icon = NAV_ICONS[item.icon];
              return (
                <li key={item.path}>
                  <NavLink to={item.path} className={navLinkClass}>
                    <Icon />
                    <span className="truncate">{item.label}</span>
                    {item.path === ROUTES.queue ? (
                      // The queue entry carries the backlog, as §23.2 draws
                      // it. aria-hidden: the header chip is the single
                      // announced depth source (CS-SH-03 / CS-SH-07 — no
                      // double announcements), so this badge stays visual.
                      <span
                        aria-hidden="true"
                        className="ml-auto rounded-full bg-surface-3 px-2 py-0.5 text-xs font-semibold tabular-nums text-fg-muted"
                      >
                        {queueDepth ?? '—'}
                      </span>
                    ) : null}
                  </NavLink>
                </li>
              );
            })}
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
  queueDepth,
  onClose,
}: {
  readonly items: readonly NavItem[];
  readonly queueDepth: number | undefined;
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
        className="absolute inset-y-0 left-0 flex w-60 flex-col gap-4 overflow-y-auto border-r border-border bg-surface-1 p-4 shadow-modal motion-safe:animate-drawer-in"
      >
        <nav aria-label="Primary">
          <NavGroups items={items} queueDepth={queueDepth} />
        </nav>
      </div>
    </div>
  );
};

// ─── The shell (CS-SH-01) — one header, one nav, one main, composed as a
// panel per the §23.2 frame: a full-width top bar whose brand cell sits
// over a full-height sidebar rail; content runs full-bleed beside it. ─────

export const AppShell = () => {
  const { principal, signOut } = useAuth();
  const location = useLocation();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // One queue subscription for the whole shell — the header chip and the
  // rail badge render the same cached figure (CS-SH-03).
  const queueQuery = useQueueQuery();
  const queueDepth = queueQuery.data?.pages[0]?.queue_depth;

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
      <div className="flex min-h-screen flex-col bg-bg">
        {/* CS-A-10 — skip link first in tab order + landmarks. */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-control focus:bg-surface-1 focus:px-3 focus:py-2 focus:text-sm focus:text-fg focus:ring-2 focus:ring-brand-400"
        >
          Skip to content
        </a>

        <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center border-b border-border bg-surface-1">
          {/* Brand cell — the §12.1 mark drawn once, in the banner. At lg+
              it aligns over the rail and carries the rail's right border, so
              the sidebar reads as one full-height panel through the bar. */}
          <div className="flex h-full items-center gap-3 px-4 lg:w-60 lg:shrink-0 lg:border-r lg:border-border">
            <button
              type="button"
              onClick={() => setIsDrawerOpen(true)}
              aria-label="Open navigation"
              aria-expanded={isDrawerOpen}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-control text-fg-muted hover:bg-surface-2 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 lg:hidden"
            >
              <MenuIcon />
            </button>
            <span className="flex min-w-0 items-center gap-2.5">
              <Logo size={22} />
              <span className="truncate text-base font-semibold tracking-tight text-fg">
                Guardian Lens
              </span>
            </span>
          </div>

          {/* CS-SH-09 — session chrome: principal + sign-out. The
              current-site element §23.2 draws beside the brand awaits a site
              field on the session payload (ApiUser carries none yet) — an
              API gap, not a shell decision. */}
          <div className="flex h-full min-w-0 flex-1 items-center justify-end gap-2 px-4 sm:gap-3 sm:px-6">
            {/* CS-SH-03 — depth is shell chrome, visible from every screen
                and at every width (CS-SH-04). */}
            <QueueDepthChip depth={queueDepth} />
            <ThemeToggle />
            <PrincipalMenu fullName={principal.fullName} onSignOut={signOut} />
          </div>
        </header>

        <div className="flex min-h-0 flex-1">
          {/* CS-SH-04 — the persistent sidebar at lg+: a full-height rail on
              its own surface, scrolling independently of the content. */}
          <nav
            aria-label="Primary"
            className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-60 shrink-0 overflow-y-auto border-r border-border bg-surface-1 px-3 py-4 lg:block"
          >
            <NavGroups items={navItems} queueDepth={queueDepth} />
          </nav>

          {/* Full-bleed working surface — a panel fills its viewport; wide
              content (the queue, tables) owns the width it is given. */}
          <main id="main" className="min-w-0 flex-1 px-4 py-5 sm:px-6 lg:px-8">
            <Outlet />
          </main>
        </div>

        {isDrawerOpen ? (
          <NavDrawer
            items={navItems}
            queueDepth={queueDepth}
            onClose={() => setIsDrawerOpen(false)}
          />
        ) : null}
      </div>
    </ToastProvider>
  );
};
