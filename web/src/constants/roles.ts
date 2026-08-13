import { ROUTES } from './routes';

export const ROLE = {
  REVIEWER: 'reviewer',
  SAFETY_MANAGER: 'safety_manager',
  SITE_ADMIN: 'site_admin',
  AUDITOR: 'auditor',
} as const;

export type Role = (typeof ROLE)[keyof typeof ROLE];

const ROLE_VALUES: readonly string[] = Object.values(ROLE);

export const isRole = (value: string): value is Role => ROLE_VALUES.includes(value);

/** TRD §12.3 — the "Decide" column: auditor is read-only, agent never appears here. */
export const DECIDING_ROLES: readonly Role[] = [
  ROLE.REVIEWER,
  ROLE.SAFETY_MANAGER,
  ROLE.SITE_ADMIN,
];

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

export interface NavItem {
  readonly path: string;
  readonly label: string;
  readonly group: NavGroup;
  readonly roles: readonly Role[];
}

/**
 * Role-aware navigation, shaped by the TRD §12.3 authorisation matrix:
 * reviewer sees the queue only; safety_manager adds reports and configuration
 * (zones/rules); site_admin sees everything; auditor gets a read-only queue
 * plus the audit view. Navigation shaping only — the API is the authorisation
 * boundary (CS-SEC-03).
 */
export const NAV_ITEMS: readonly NavItem[] = [
  {
    path: ROUTES.queue,
    label: 'Review queue',
    group: NAV_GROUP.REVIEW,
    roles: [ROLE.REVIEWER, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN, ROLE.AUDITOR],
  },
  {
    path: ROUTES.reports,
    label: 'Reports',
    group: NAV_GROUP.RECORDS,
    roles: [ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN],
  },
  {
    path: ROUTES.config,
    label: 'Configuration',
    group: NAV_GROUP.ADMINISTRATION,
    roles: [ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN],
  },
  {
    path: ROUTES.audit,
    label: 'Audit log',
    group: NAV_GROUP.ADMINISTRATION,
    roles: [ROLE.AUDITOR, ROLE.SAFETY_MANAGER, ROLE.SITE_ADMIN],
  },
];
