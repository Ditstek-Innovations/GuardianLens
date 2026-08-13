import { StatusChip } from '@/components/StatusChip';
import { RowButton } from '@/components/ui';
import { formatConfidence } from '@/lib/format/formatConfidence';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import type { QueueEventItem } from '@/lib/api/types';

export interface QueueRowProps {
  readonly item: QueueEventItem;
  readonly isSelected: boolean;
  readonly onSelect: (eventId: string) => void;
  readonly registerRow: (eventId: string, element: HTMLButtonElement | null) => void;
}

export const QueueRow = ({ item, isSelected, onSelect, registerRow }: QueueRowProps) => {
  const handleClick = (): void => {
    onSelect(item.id);
  };
  const handleRef = (element: HTMLButtonElement | null): void => {
    registerRow(item.id, element);
  };

  return (
    <li>
      <RowButton
        ref={handleRef}
        onClick={handleClick}
        aria-current={isSelected ? 'true' : undefined}
        // Functional marker (not a test id): lets the page-level Enter
        // shortcut defer to native button activation on a focused row.
        data-queue-row="true"
        // §12.1 — the selected row carries the brand left rail + surface-2.
        className={isSelected ? 'border-brand-400 bg-surface-2' : undefined}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-fg">
              {item.camera.name} · {item.zone.name}
            </p>
            <p className="truncate text-sm text-fg-muted">{item.rule.human_readable}</p>
            <p className="mt-0.5 text-xs tabular-nums text-fg-muted">
              {formatTimestamp(item.occurred_at, item.site_timezone)}
              {' · '}
              {/* BR-V-03 — confidence annotates only; it plays no part in disposition. */}
              <span>Confidence {formatConfidence(item.confidence)}</span>
            </p>
          </div>
          <StatusChip status={item.status} />
        </div>
      </RowButton>
    </li>
  );
};
