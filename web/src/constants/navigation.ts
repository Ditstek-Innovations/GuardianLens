import { ROLE } from './roles';
import { ROUTES } from './routes';

import type { Role } from './roles';

/** CS-SH-02 — navigation is grouped Review · Records · Administration. */
export const NAV_GROUP = {
  REVIEW: 'review',
  RECORDS: 'records',
  ADMINISTRATION: 'administration',
} as const;

export type NavGroup = (typeof NAV_GROUP)[keyof typeof NAV_GROUP];

export const NAV_GROUP_ORDER: readonly { readonly id: NavGroup; readonly label: string }[] = [
  { id: NAV_GROUP.REVIEW, label: 'Review' },
  { id: NAV_GROUP.RECORDS, label: 'Records' },
  { id: NAV_GROUP.ADMINISTRATION, label: 'Administration' },
];

/**
 * Icon identity per nav entry. The drawings live in the shell (inline SVG,
 * §12.1 — no icon font, no external asset); this file stays pure data.
 */
export type NavIconName = 'queue' | 'live' | 'history' | 'reports' | 'configuration' | 'audit';

export interface NavItem {
  readonly path: string;
  readonly label: string;
  readonly icon: NavIconName;
  readonly group: NavGroup;
  readonly roles: readonly Role[];
}

/**
 * CS-SH-02 — THE navigation declaration; no component inlines a nav list.
 * Role-aware, shaped by the TRD §12.3 authorisation matrix: reviewer sees the
 * queue only; safety_manager adds reports and configuration (zones/rules);
 * site_admin sees everything; auditor gets a read-only queue plus the audit
 * view. Navigation shaping only — the API is the authorisation boundary
 * (CS-SEC-03).
 */
export const NAV_ITEMS: readonly NavItem[] = [
  {
    path: ROUTES.queue,
    label: 'Review queue',
    icon: 'queue',
    group: NAV_GROUP.REVIEW,
    roles: [ROLE.REVIEWER, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN, ROLE.AUDITOR],
  },
  {
    path: ROUTES.liveFeeding,
    label: 'Live feeding',
    icon: 'live',
    group: NAV_GROUP.REVIEW,
    roles: [ROLE.REVIEWER, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN, ROLE.AUDITOR],
  },
  {
    path: ROUTES.history,
    label: 'Event history',
    icon: 'history',
    group: NAV_GROUP.RECORDS,
    // §23.4 — every role reads history; the auditor's view is read-only by
    // construction (no decision affordance exists on decided events).
    roles: [ROLE.REVIEWER, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN, ROLE.AUDITOR],
  },
  {
    path: ROUTES.reports,
    label: 'Reports',
    icon: 'reports',
    group: NAV_GROUP.RECORDS,
    roles: [ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN],
  },
  {
    path: ROUTES.config,
    label: 'Configuration',
    icon: 'configuration',
    group: NAV_GROUP.ADMINISTRATION,
    roles: [ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN],
  },
  {
    path: ROUTES.audit,
    label: 'Audit log',
    icon: 'audit',
    group: NAV_GROUP.ADMINISTRATION,
    roles: [ROLE.AUDITOR, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN],
  },
];
