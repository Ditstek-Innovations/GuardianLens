import { Spinner } from '@/components/ui';

export interface EvidenceFrameProps {
  readonly url: string | null;
  readonly isPending: boolean;
  readonly isError: boolean;
  readonly alt: string;
  readonly onLoaded: () => void;
  readonly onFailed: () => void;
}

const ImageOffIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="28"
    height="28"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m3 3 18 18" />
    <path d="M9.5 4H19a2 2 0 0 1 2 2v9.5" />
    <path d="M21 19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7" />
    <path d="m6 15 3-3 2.5 2.5" />
    <circle cx="15" cy="9" r="1.5" />
  </svg>
);

/**
 * ADR-013 / ARCHITECTURE §6.3 F-6 — decision controls stay disabled until this
 * frame has actually rendered, and retrieval failure is an explicit state.
 * Never a silent broken image: a decision taken without the reviewer having
 * seen the evidence is attribution without basis.
 *
 * §12.1 — the frame sits in a radius-12 card with a hairline border on
 * surface-1; a quiet checkerboard backdrop reads as "image surface" while
 * the frame loads (no layout shift on resolve — CS-P-03).
 */
export const EvidenceFrame = ({
  url,
  isPending,
  isError,
  alt,
  onLoaded,
  onFailed,
}: EvidenceFrameProps) => {
  if (isError) {
    // CS-Y-13 — the failure is a designed state, never a broken image.
    return (
      <div
        role="alert"
        className="flex aspect-video items-center justify-center rounded-card border border-danger bg-danger-subtle p-6 text-center"
      >
        <div className="flex flex-col items-center">
          <span className="text-danger">
            <ImageOffIcon />
          </span>
          <p className="mt-3 font-medium text-danger">Evidence unavailable — storage failure</p>
          <p className="mt-1 max-w-md text-sm text-danger">
            Decisions stay disabled: a candidate cannot be decided without its evidence frame
            (ADR-013).
          </p>
        </div>
      </div>
    );
  }

  if (isPending || url === null) {
    return (
      <div
        aria-label="Loading evidence frame"
        className="flex aspect-video items-center justify-center rounded-card border border-border bg-checker shadow-ambient"
      >
        <span className="flex items-center gap-2 rounded-full bg-surface-1 px-4 py-2 text-sm text-fg-muted">
          <Spinner />
          Loading evidence frame…
        </span>
      </div>
    );
  }

  // CS-P-03 — fixed aspect box so the decision bar does not shift as the
  // image lands. CS-A-07 — alt states camera, zone and timestamp.
  return (
    <img
      src={url}
      alt={alt}
      onLoad={onLoaded}
      onError={onFailed}
      className="aspect-video w-full rounded-card border border-border bg-checker object-contain shadow-ambient"
    />
  );
};
