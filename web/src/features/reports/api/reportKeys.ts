import type { ReportParams } from '../types';

// CS-D-03 — key factory.
export const reportKeys = {
  all: ['reports'] as const,
  summary: (params: ReportParams) => [...reportKeys.all, 'summary', params] as const,
};
