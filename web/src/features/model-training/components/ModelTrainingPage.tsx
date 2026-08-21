import { PageHeading } from "@/components/layout/PageHeading";
import { Chip, ErrorState, Skeleton } from "@/components/ui";
import { usePageTitle } from "@/hooks/usePageTitle";

import { useModelTraining } from "../api/useModelTraining";

const STATE_LABELS: Record<string, string> = {
  not_started: "Not started",
  collecting: "Collecting reviewed images",
  training: "Training in progress",
  candidate_ready: "Candidate ready",
  failed: "Training failed",
};

const Metric = ({
  label,
  value,
}: {
  readonly label: string;
  readonly value: number;
}) => (
  <div className="rounded-card border border-border bg-surface-1 p-4 shadow-ambient">
    <dt className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
      {label}
    </dt>
    <dd className="mt-1 text-3xl font-semibold tabular-nums text-fg">
      {value}
    </dd>
  </div>
);

export const ModelTrainingPage = () => {
  usePageTitle("Model training");
  const query = useModelTraining();

  if (query.isPending) {
    return (
      <Skeleton
        className="h-72 w-full"
        aria-label="Loading model training status"
      />
    );
  }
  if (query.isError || query.data === undefined) {
    return (
      <ErrorState
        title="Model training status could not be loaded."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data;
  const collectionPercent = Math.min(
    100,
    Math.round((data.eligible / data.minimum_samples) * 100),
  );
  const trainingPercent = data.progress_percent ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <PageHeading>Model training</PageHeading>
          <p className="mt-1 max-w-3xl text-sm text-fg-muted">
            Reviewer decisions continuously build a labelled dataset. Training
            runs in batches and creates a candidate model; the live detector
            changes only after validation and deployment.
          </p>
        </div>
        <Chip variant={data.worker_state === "failed" ? "warn" : "brand"}>
          {STATE_LABELS[data.worker_state] ?? data.worker_state}
        </Chip>
      </div>

      <dl className="grid gap-3 sm:grid-cols-3">
        <Metric label="Decisions collected" value={data.reviewed} />
        <Metric label="Training ready" value={data.eligible} />
        <Metric label="Safely excluded" value={data.excluded} />
      </dl>

      <section className="rounded-card border border-border bg-surface-1 p-5 shadow-ambient">
        <h2 className="text-lg font-semibold text-fg">
          {data.worker_state === "training"
            ? "Candidate training progress"
            : "Next training batch"}
        </h2>
        <div
          className="mt-4 h-3 overflow-hidden rounded-full bg-surface-3"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={
            data.worker_state === "training"
              ? trainingPercent
              : collectionPercent
          }
        >
          <div
            className="duration-500 h-full rounded-full bg-brand-500 transition-[width]"
            style={{
              width: `${data.worker_state === "training" ? trainingPercent : collectionPercent}%`,
            }}
          />
        </div>
        <p className="mt-2 text-sm text-fg-muted">
          {data.worker_state === "training"
            ? `Epoch ${data.current_epoch ?? 0} of ${data.total_epochs ?? "—"} (${trainingPercent.toFixed(0)}%)`
            : `${data.eligible} of ${data.minimum_samples} eligible decisions collected`}
        </p>
        {data.worker_detail !== null ? (
          <p className="mt-1 text-sm text-fg-muted">{data.worker_detail}</p>
        ) : null}
      </section>

      <section className="rounded-card border border-border bg-surface-1 p-5 shadow-ambient">
        <h2 className="text-lg font-semibold text-fg">
          Training data by class
        </h2>
        {Object.keys(data.by_class).length === 0 ? (
          <p className="mt-3 text-sm text-fg-muted">
            No eligible post-update decisions yet.
          </p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(data.by_class).map(([name, count]) => (
              <Chip key={name} variant="neutral">
                {name}: {count}
              </Chip>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-card border border-border bg-surface-1 p-5 shadow-ambient">
        <h2 className="text-lg font-semibold text-fg">How feedback is used</h2>
        <ol className="mt-3 grid gap-3 text-sm sm:grid-cols-4">
          <li className="rounded-control bg-surface-2 p-3 text-fg">
            <strong>1. Review</strong>
            <br />
            <span className="text-fg-muted">
              Accept and Correct add positive labels. Individual Reject adds a
              false-positive example.
            </span>
          </li>
          <li className="rounded-control bg-surface-2 p-3 text-fg">
            <strong>2. Train</strong>
            <br />
            <span className="text-fg-muted">
              At {data.minimum_samples} eligible images, the worker fine-tunes
              YOLO in the background.
            </span>
          </li>
          <li className="rounded-control bg-surface-2 p-3 text-fg">
            <strong>3. Validate</strong>
            <br />
            <span className="text-fg-muted">
              The new weights remain a candidate until accuracy is evaluated.
            </span>
          </li>
          <li className="rounded-control bg-surface-2 p-3 text-fg">
            <strong>4. Deploy</strong>
            <br />
            <span className="text-fg-muted">
              Deployment is explicit, so bad feedback cannot silently replace
              the live model.
            </span>
          </li>
        </ol>
        {data.candidate_path !== null ? (
          <p className="mt-4 break-all text-xs text-fg-muted">
            Latest candidate:{" "}
            <span className="font-mono">{data.candidate_path}</span> ·{" "}
            {data.deployed ? "deployed" : "not deployed"}
          </p>
        ) : null}
        {data.updated_at !== null ? (
          <p className="mt-2 text-xs text-fg-faint">
            Updated {new Date(data.updated_at).toLocaleString()}
          </p>
        ) : null}
      </section>
    </div>
  );
};
