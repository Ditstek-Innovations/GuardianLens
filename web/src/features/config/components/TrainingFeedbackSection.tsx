import { Chip, ErrorState, Skeleton } from '@/components/ui';

import { useTrainingFeedback } from '../api/useTrainingFeedback';

const STATE_LABELS: Record<string, string> = {
  not_started: 'Not started',
  collecting: 'Collecting feedback',
  training: 'Training candidate',
  candidate_ready: 'Candidate ready',
  failed: 'Training failed',
};

export const TrainingFeedbackSection = () => {
  const query = useTrainingFeedback();

  return (
    <section
      aria-label="Training feedback"
      className="overflow-hidden rounded-card border border-border bg-surface-1 shadow-ambient"
    >
      <div className="border-b border-border px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-fg">Training feedback</h2>
            <p className="mt-0.5 text-sm text-fg-muted">
              Human-approved crops train a separate YOLO candidate. Live detection is unchanged
              until that candidate is evaluated and deployed.
            </p>
          </div>
          {query.data !== undefined ? (
            <Chip variant={query.data.worker_state === 'failed' ? 'warn' : 'brand'}>
              {STATE_LABELS[query.data.worker_state] ?? query.data.worker_state}
            </Chip>
          ) : null}
        </div>
      </div>
      {query.isPending ? (
        <div aria-label="Loading training feedback" className="space-y-2 p-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-2/3" />
        </div>
      ) : query.isError || query.data === undefined ? (
        <div className="p-4">
          <ErrorState
            title="Training feedback could not be loaded."
            onRetry={() => void query.refetch()}
          />
        </div>
      ) : (
        <div className="space-y-3 p-4">
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-xs uppercase tracking-wide text-fg-muted">Reviewed</dt>
              <dd className="text-xl font-semibold tabular-nums text-fg">{query.data.reviewed}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-fg-muted">Training ready</dt>
              <dd className="text-xl font-semibold tabular-nums text-fg">{query.data.eligible}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-fg-muted">Excluded safely</dt>
              <dd className="text-xl font-semibold tabular-nums text-fg">{query.data.excluded}</dd>
            </div>
          </dl>
          <div className="flex flex-wrap gap-2">
            {Object.entries(query.data.by_class).map(([name, count]) => (
              <Chip key={name} variant="neutral">
                {name}: {count}
              </Chip>
            ))}
          </div>
          {query.data.worker_detail !== null ? (
            <p className="text-sm text-fg-muted">{query.data.worker_detail}</p>
          ) : null}
          {query.data.candidate_path !== null ? (
            <p className="text-xs text-fg-muted">
              Candidate: <span className="font-mono">{query.data.candidate_path}</span> · not
              deployed
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
};
