import { cn } from '@/lib/utils/cn';

export interface DecisionMixBarProps {
  readonly counts: {
    readonly accepted: number;
    readonly corrected: number;
    readonly rejected: number;
  };
}

interface Segment {
  readonly key: 'accepted' | 'corrected' | 'rejected';
  readonly label: string;
  /** The StatusChip vocabulary — accepted:ok, corrected:brand, rejected:danger. */
  readonly fillClass: string;
}

// These are decision states, so they wear the status/brand tokens the rest of
// the product uses for the same states (StatusChip) — never the categorical
// chart palette (CS-Y-11). Identity is carried by the text labels below the
// bar, not by colour alone (NFR-ACC-02).
const SEGMENTS: readonly Segment[] = [
  { key: 'accepted', label: 'Accepted', fillClass: 'bg-ok' },
  { key: 'corrected', label: 'Corrected', fillClass: 'bg-brand-mark' },
  { key: 'rejected', label: 'Rejected', fillClass: 'bg-danger' },
];

/**
 * BR-R-03 / CS-B-09 — all three dispositions of the period, always visible,
 * as one 100% bar. Segments keep a 2px surface gap; each is named with its
 * count and share in text ink.
 */
export const DecisionMixBar = ({ counts }: DecisionMixBarProps) => {
  const total = counts.accepted + counts.corrected + counts.rejected;

  if (total === 0) {
    return <p className="text-sm text-fg-muted">No decisions were made in this period.</p>;
  }

  const share = (count: number): number => Math.round((count / total) * 100);

  return (
    <div className="space-y-3">
      <div
        role="img"
        aria-label={`Decision mix: ${counts.accepted} accepted, ${counts.corrected} corrected, ${counts.rejected} rejected`}
        className="flex h-4 w-full gap-0.5 overflow-hidden rounded-full"
      >
        {SEGMENTS.filter((segment) => counts[segment.key] > 0).map((segment) => (
          <span
            key={segment.key}
            className={cn('h-full', segment.fillClass)}
            style={{ width: `${(counts[segment.key] / total) * 100}%`, minWidth: '4px' }}
          />
        ))}
      </div>
      <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
        {SEGMENTS.map((segment) => (
          <div key={segment.key} className="flex items-center gap-1.5">
            <span aria-hidden="true" className={cn('h-2 w-2 rounded-full', segment.fillClass)} />
            <dt className="text-fg-muted">{segment.label}</dt>
            <dd className="font-medium tabular-nums text-fg">
              {counts[segment.key]}
              <span className="font-normal text-fg-muted"> · {share(counts[segment.key])}%</span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
};
