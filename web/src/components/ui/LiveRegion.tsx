export interface LiveRegionProps {
  readonly message: string;
}

/**
 * CS-A-06 — async state changes announce via aria-live: a reviewer must know
 * a decision was recorded without watching for a visual flash.
 */
export const LiveRegion = ({ message }: LiveRegionProps) => (
  <div aria-live="polite" role="status" className="sr-only">
    {message}
  </div>
);
