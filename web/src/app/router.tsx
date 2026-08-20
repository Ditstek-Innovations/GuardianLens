import { Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/layout/AppShell';
import { ROLE } from '@/constants/roles';
import { ROUTE_PATTERNS, ROUTES } from '@/constants/routes';
import { AuditPage } from '@/features/audit';
import { ForgotPasswordPage, LoginPage, ResetPasswordPage, SignupPage } from '@/features/auth';
import { ConfigPage } from '@/features/config';
import { EventDetailPage } from '@/features/event-detail';
import { HistoryPage } from '@/features/event-history';
import { LiveFeedingPage } from '@/features/live-feeding';
import { QueuePage } from '@/features/review-queue';
import { ReportsPage } from '@/features/reports';
import { CameraDiscovery } from '@/features/cameras';

import { RequireAuth, RequireRole } from './guards';

/*
 * ───────────────────────────────────────────────────────────────────────────
 * COMPONENTS THAT MUST NOT EXIST — asserted by their absence
 * (TRD §7.4 "Components that must not be built" · RULE_BOOK §4.4 · PRD §4.5)
 *
 * The following have no route, no component, no API call and no dead code
 * path anywhere in this application. Their absence is the product:
 *
 *   1. Bulk select / select-all / multi-select / bulk decision controls —
 *      BR-V-02, FR-047, DP-3. No interface may decide more than one
 *      candidate in a single act.
 *   2. Auto-approve / auto-dismiss of any kind, including any
 *      confidence-based auto-dispose toggle — BR-V-03, FR-048, AP-4.
 *      Confidence may order or annotate; it never decides.
 *   3. Supervisor override / second-approver flow — BR-V-04, TRD §11.4.
 *      A decided event is immutable (BR-V-01).
 *   4. Any per-person or per-reviewer productivity display — dashboards,
 *      leaderboards, "events reviewed today per user" — BR-002.
 *   5. Video playback. Evidence is a single still frame, never video —
 *      RULE_BOOK §3.1 "Evidence Frame", BR-008.
 *
 * Do not add these behind a flag, an environment variable or a role check:
 * they must be absent from the build, not disabled within it (CS-ENV-04,
 * CS-B-01…CS-B-04). Tests assert the absence (CS-Q-10).
 * ───────────────────────────────────────────────────────────────────────────
 */

const CompassIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="32"
    height="32"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="9" />
    <path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" />
  </svg>
);

const NotFound = () => (
  // CS-RT-05 / CS-SC-05 — unknown paths render a designed not-found screen,
  // outside the shell with no navigation (CS-SC-02).
  <div className="flex min-h-screen items-center justify-center bg-bg p-8">
    <div className="flex w-full max-w-md flex-col items-center rounded-card border border-border bg-surface-1 px-8 py-14 text-center shadow-ambient">
      <span className="text-fg-faint">
        <CompassIcon />
      </span>
      <h1 className="mt-3 text-2xl font-semibold text-fg">Page not found</h1>
      <p className="mt-2 text-sm text-fg-muted">
        This address does not match any screen. The review queue is home.
      </p>
      <a
        href={ROUTES.queue}
        className="mt-5 inline-flex h-11 items-center rounded-control bg-brand-500 px-4 text-sm font-semibold text-brand-fill-ink shadow-glow hover:bg-brand-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 motion-safe:transition motion-safe:duration-120 motion-safe:ease-out"
      >
        Go to the review queue
      </a>
    </div>
  </div>
);

export const AppRouter = () => (
  <Routes>
    {/* SCR-1…SCR-1c — the public auth family, outside AppShell (CS-AU-01).
        CS-AU-18: these screens link only to each other; no application
        screen links back to sign-up. */}
    <Route path={ROUTES.login} element={<LoginPage />} />
    <Route path={ROUTES.signup} element={<SignupPage />} />
    <Route path={ROUTES.forgotPassword} element={<ForgotPasswordPage />} />
    <Route path={ROUTES.resetPassword} element={<ResetPasswordPage />} />
    <Route
      element={
        <RequireAuth>
          <AppShell />
        </RequireAuth>
      }
    >
      {/* TRD §7.2 — the queue is home. */}
      <Route path="/" element={<Navigate to={ROUTES.queue} replace />} />
      <Route path={ROUTES.queue} element={<QueuePage />} />
      <Route path={ROUTES.liveFeeding} element={<LiveFeedingPage />} />
      <Route path={ROUTE_PATTERNS.queueEvent} element={<EventDetailPage />} />
      {/* SCR-4 — every authenticated role reads history (§23.4). */}
      <Route path={ROUTES.history} element={<HistoryPage />} />
      <Route
        path={ROUTES.reports}
        element={
          <RequireRole roles={[ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN]}>
            <ReportsPage />
          </RequireRole>
        }
      />
      <Route
        path={ROUTE_PATTERNS.cameraDiscovery}
        element={
          <RequireRole roles={[ROLE.SITE_ADMIN]}>
            <div className="mx-auto max-w-5xl">
              <CameraDiscovery />
            </div>
          </RequireRole>
        }
      />
      <Route
        path={ROUTES.config}
        element={
          <RequireRole roles={[ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN]}>
            <ConfigPage />
          </RequireRole>
        }
      />
      <Route
        path={ROUTES.audit}
        element={
          <RequireRole roles={[ROLE.AUDITOR, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN]}>
            <AuditPage />
          </RequireRole>
        }
      />
    </Route>
    <Route path="*" element={<NotFound />} />
  </Routes>
);
