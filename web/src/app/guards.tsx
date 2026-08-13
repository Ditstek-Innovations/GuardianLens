import { Link, Navigate, useLocation } from 'react-router-dom';

import { PageHeading } from '@/components/layout/PageHeading';
import { ROUTES } from '@/constants/routes';
import { useAuth } from '@/hooks/useAuth';
import { usePageTitle } from '@/hooks/usePageTitle';

import type { ReactNode } from 'react';
import type { Role } from '@/constants/roles';

const LockIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="28"
    height="28"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="4" y="10.5" width="16" height="10" rx="2" />
    <path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" />
  </svg>
);

/**
 * CS-SC-05 — an explicit "you do not have access" screen with a route back
 * to the queue; never a blank page, never a silent redirect. Renders inside
 * the shell, so navigation and queue depth stay visible.
 */
const AccessDeniedScreen = () => {
  usePageTitle('No access');

  return (
    <section
      aria-label="No access"
      className="flex flex-col items-center rounded-card border border-border bg-surface-1 px-8 py-14 text-center shadow-ambient"
    >
      <span className="text-fg-faint">
        <LockIcon />
      </span>
      <div className="mt-3">
        <PageHeading>You do not have access to this screen</PageHeading>
      </div>
      <p className="mt-2 max-w-md text-sm text-fg-muted">
        Your role does not include this area. Access is decided by the server, not this screen — if
        you believe you need it, ask a site admin to adjust your role.
      </p>
      <Link
        to={ROUTES.queue}
        className="mt-5 inline-flex h-11 items-center rounded-control bg-brand-500 px-4 text-sm font-semibold text-brand-fill-ink shadow-glow hover:bg-brand-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 motion-safe:transition motion-safe:duration-120 motion-safe:ease-out"
      >
        Back to the review queue
      </Link>
    </section>
  );
};

/**
 * CS-RT-06 / CS-SEC-03 — these guards shape navigation only. The API is the
 * authorisation boundary; a forged client gains nothing here.
 */
export const RequireAuth = ({ children }: { children: ReactNode }) => {
  const { principal, restoring } = useAuth();
  const location = useLocation();
  // Mid-restore the session may still be valid — redirecting to login now
  // would turn every hard reload into a logout. Nothing renders until the
  // restore settles (it is a single request, CS-AU-07).
  if (restoring) return null;
  if (principal === null) {
    return <Navigate to={ROUTES.login} replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
};

export const RequireRole = ({
  roles,
  children,
}: {
  roles: readonly Role[];
  children: ReactNode;
}) => {
  const { principal } = useAuth();
  if (principal === null || !principal.roles.some((role) => roles.includes(role))) {
    return <AccessDeniedScreen />;
  }
  return <>{children}</>;
};
