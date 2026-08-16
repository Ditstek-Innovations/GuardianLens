import { Chip, RowButton } from '@/components/ui';
import { formatConfidence } from '@/lib/format/formatConfidence';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import type { IncidentGroup } from '@/lib/api/types';

export interface IncidentRowProps {
  readonly incident: IncidentGroup;
  readonly isSelected: boolean;
  readonly onSelect: (incident: IncidentGroup) => void;
  readonly registerRow: (key: string, element: HTMLButtonElement | null) => void;
}

/**
 * One ongoing condition as one row. Opening it walks the members one by
 * one — the count is information, never a decision affordance (BR-V-02).
 */
export const IncidentRow = ({
  incident,
  isSelected,
  onSelect,
  registerRow,
}: IncidentRowProps) => {
  const handleClick = (): void => {
    onSelect(incident);
  };
  const handleRef = (element: HTMLButtonElement | null): void => {
    registerRow(incident.incident_key, element);
  };
  const isOngoing = incident.count > 1;

  return (
    <li>
      <RowButton
        ref={handleRef}
        onClick={handleClick}
        aria-current={isSelected ? 'true' : undefined}
        data-queue-row="true"
        className={isSelected ? 'border-brand-400 bg-surface-2' : undefined}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-fg">
              {incident.rule.human_readable ?? 'Rule no longer configured'}
            </p>
            <p className="truncate text-sm text-fg-muted">
              {incident.camera.name}
              {incident.zone.name !== null ? ` · ${incident.zone.name}` : ''}
            </p>
            <p className="mt-0.5 text-xs tabular-nums text-fg-muted">
              {isOngoing
                ? `${formatTimestamp(incident.first_occurred_at)} – ${formatTimestamp(
                    incident.last_occurred_at,
                  )}`
                : formatTimestamp(incident.first_occurred_at)}
              {incident.max_confidence !== null ? (
                <>
                  {' · '}
                  {/* BR-V-03 — annotation only; never part of any disposition. */}
                  <span>Max confidence {formatConfidence(incident.max_confidence)}</span>
                </>
              ) : null}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Chip variant={isOngoing ? 'brand' : 'neutral'} className="tabular-nums">
              {incident.count} {incident.count === 1 ? 'candidate' : 'candidates'}
            </Chip>
          </div>
        </div>
      </RowButton>
    </li>
  );
};
