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
