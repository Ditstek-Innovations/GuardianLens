import { GROUP_LABEL, groupName } from '../types';

import type { GroupBy } from '../types';
import type { ReportGroup } from '@/lib/api/types';

export interface VerifiedBarChartProps {
  readonly groups: readonly ReportGroup[];
  readonly groupBy: GroupBy;
}

/**
 * Verified records by one dimension — a single-series bar list. One measure,
 * one hue (chart-1; CS-Y-11 fixed order, never cycled), no legend (the title
 * names the series), every value directly labelled in text ink so identity
 * and magnitude never depend on colour. Days read chronologically; the other
 * dimensions read largest-first. The adjacent table is the accessible
 * long-form view of the same data.
 */
export const VerifiedBarChart = ({ groups, groupBy }: VerifiedBarChartProps) => {
  const sorted =
    groupBy === 'day'
      ? [...groups].sort((a, b) => groupName(a).localeCompare(groupName(b)))
      : [...groups].sort((a, b) => b.verified_count - a.verified_count);
  const max = Math.max(...sorted.map((group) => group.verified_count), 1);

  return (
    <ol
      aria-label={`Verified records by ${GROUP_LABEL[groupBy].toLowerCase()}`}
      className="space-y-1"
    >
      {sorted.map((group) => {
        const name = groupName(group);
        const percent = (group.verified_count / max) * 100;
        return (
          <li
            key={name}
            className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-3 rounded-control px-2 py-1.5 motion-safe:transition-colors motion-safe:duration-120 hover:bg-surface-2"
          >
            <span className="truncate text-sm text-fg-muted" title={name}>
              {name}
            </span>
            {/* Track: hairline baseline on the left; the bar is thin with a
                rounded data-end and a square anchor at the baseline. */}
            <span aria-hidden="true" className="relative h-4 border-l border-border-strong">
              {group.verified_count > 0 ? (
                <span
                  className="absolute inset-y-0 left-0 rounded-r-sm bg-chart-1"
                  style={{ width: `max(${percent}%, 3px)` }}
                />
              ) : null}
            </span>
            <span className="text-sm font-medium tabular-nums text-fg">
              {group.verified_count}
            </span>
          </li>
        );
      })}
    </ol>
  );
};
