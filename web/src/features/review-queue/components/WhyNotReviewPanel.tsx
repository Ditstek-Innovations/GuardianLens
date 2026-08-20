import { Chip, ChipIcon } from '@/components/ui';

import type { WhyNotReview } from '@/lib/api/types';

export const WhyNotReviewPanel = ({ rows }: { readonly rows: readonly WhyNotReview[] }) => {
  if (rows.length === 0) return null;
  return (
    <section
      aria-label="Why nothing is in Review"
      className="rounded-card border border-border bg-surface-1 p-4 shadow-ambient"
    >
      <h2 className="text-sm font-semibold text-fg">Why Review is empty</h2>
      <p className="mt-1 text-sm text-fg-muted">
        A camera only creates a review item when a frame matches an active rule.
        This is the latest reason from the edge agent, updated with each health
        beat.
      </p>
      <ul className="mt-3 space-y-3">
        {rows.map((row) => (
          <li key={row.camera_id} className="rounded-lg border border-border px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-fg">{row.camera_name}</span>
              <Chip
                variant={row.stream === 'online' ? 'ok' : 'danger'}
                icon={<ChipIcon glyph={row.stream === 'online' ? 'check' : 'cross'} />}
              >
                {row.stream === 'online' ? 'Stream online' : 'Stream down'}
              </Chip>
            </div>
            {row.watched_classes.length > 0 ? (
              <p className="mt-1 text-xs text-fg-muted">
                Rule watches: {row.watched_classes.join(', ')}
              </p>
            ) : null}
            {row.last_seen_classes.length > 0 ? (
              <p className="mt-0.5 text-xs text-fg-muted">
                YOLO last saw: {row.last_seen_classes.join(', ')}
              </p>
            ) : (
              <p className="mt-0.5 text-xs text-fg-muted">YOLO last saw: nothing yet</p>
            )}
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-sm text-fg">
              {(row.matched
                ? ['Rule matched — the item should appear after ingest.']
                : row.why_not_review.length > 0
                  ? row.why_not_review
                  : ['No miss detail yet. Wait for the next health beat.']
              ).map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
};
