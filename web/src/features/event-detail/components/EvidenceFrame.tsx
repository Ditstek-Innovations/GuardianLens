import { useRef } from 'react';

import { Spinner } from '@/components/ui';
import { formatConfidence } from '@/lib/format/formatConfidence';

import type { SyntheticEvent } from 'react';

export interface EvidenceFrameProps {
  readonly url: string | null;
  readonly isPending: boolean;
  readonly isError: boolean;
  readonly alt: string;
  readonly onLoaded: () => void;
  readonly onFailed: () => void;
  readonly prediction?: {
    readonly className: string;
    readonly confidence: number;
    readonly bbox: readonly [number, number, number, number];
  } | null;
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
  prediction = null,
}: EvidenceFrameProps) => {
  const zoomCanvasRef = useRef<HTMLCanvasElement>(null);

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

  const handleImageLoaded = (event: SyntheticEvent<HTMLImageElement>): void => {
    if (prediction !== null && zoomCanvasRef.current !== null) {
      const image = event.currentTarget;
      const [x1, y1, x2, y2] = prediction.bbox;
      const sourceX = Math.max(0, Math.round(x1 * image.naturalWidth));
      const sourceY = Math.max(0, Math.round(y1 * image.naturalHeight));
      const sourceWidth = Math.max(
        1,
        Math.min(image.naturalWidth - sourceX, Math.round((x2 - x1) * image.naturalWidth)),
      );
      const sourceHeight = Math.max(
        1,
        Math.min(image.naturalHeight - sourceY, Math.round((y2 - y1) * image.naturalHeight)),
      );
      const canvas = zoomCanvasRef.current;
      canvas.width = sourceWidth;
      canvas.height = sourceHeight;
      const context = canvas.getContext('2d');
      context?.drawImage(
        image,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        0,
        0,
        sourceWidth,
        sourceHeight,
      );
    }
    onLoaded();
  };

  if (isPending || url === null) {
    return (
      <div
        aria-label="Loading evidence frame"
        className="bg-checker flex aspect-video items-center justify-center rounded-card border border-border shadow-ambient"
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
    <div className="bg-checker relative aspect-video w-full overflow-hidden rounded-card border border-border shadow-ambient">
      <img
        src={url}
        alt={alt}
        onLoad={handleImageLoaded}
        onError={onFailed}
        className="h-full w-full object-contain"
      />
      {prediction !== null ? (
        <div
          aria-label={`${prediction.className} prediction`}
          className="pointer-events-none absolute border-2 border-ok shadow-glow"
          style={{
            left: `${prediction.bbox[0] * 100}%`,
            top: `${prediction.bbox[1] * 100}%`,
            width: `${(prediction.bbox[2] - prediction.bbox[0]) * 100}%`,
            height: `${(prediction.bbox[3] - prediction.bbox[1]) * 100}%`,
          }}
        >
          <span className="absolute bottom-full left-[-2px] bg-ok-solid px-1.5 py-0.5 text-xs font-semibold text-white">
            {prediction.className} · {formatConfidence(prediction.confidence)}
          </span>
        </div>
      ) : null}
      {prediction !== null ? (
        <div className="pointer-events-none absolute right-3 top-3 w-40 overflow-hidden rounded-control border-2 border-ok bg-black shadow-modal sm:w-56">
          <div className="flex items-center justify-between gap-2 bg-ok-solid px-2 py-1 text-xs font-semibold text-white">
            <span className="truncate">Zoom · {prediction.className}</span>
            <span className="shrink-0 tabular-nums">
              {formatConfidence(prediction.confidence)}
            </span>
          </div>
          <canvas
            ref={zoomCanvasRef}
            role="img"
            aria-label={`Magnified ${prediction.className} detection`}
            className="block max-h-44 w-full bg-black object-contain"
          />
        </div>
      ) : null}
    </div>
  );
};
