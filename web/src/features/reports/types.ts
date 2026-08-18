import type { ReportGroup } from '@/lib/api/types';

export const GROUP_BY_OPTIONS = ['zone', 'rule', 'day', 'shift'] as const;
export type GroupBy = (typeof GROUP_BY_OPTIONS)[number];

export const GROUP_LABEL: Record<GroupBy, string> = {
  zone: 'Zone',
  rule: 'Rule',
  day: 'Day',
  shift: 'Shift',
};

/** The server sets exactly one dimension field per group row (TRD §10.5). */
export const groupName = (group: ReportGroup): string =>
  group.zone ?? group.rule ?? group.day ?? group.shift ?? '—';

export interface ReportParams {
  readonly from: string;
  readonly to: string;
  readonly groupBy: GroupBy;
  /**
   * ASSUMPTION A-5 — TRD §10.5 marks site_id required, but §10.6 gives the
   * sites list to site_admin only. For other roles the UI omits site_id and
   * relies on the server scoping the report to the caller's site.
   */
  readonly siteId: string | null;
}
