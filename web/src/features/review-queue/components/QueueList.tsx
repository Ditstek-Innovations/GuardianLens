import { QueueRow } from './QueueRow';

import type { QueueEventItem } from '@/lib/api/types';

export interface QueueListProps {
  readonly items: readonly QueueEventItem[];
  readonly selectedId: string | undefined;
  readonly onSelect: (eventId: string) => void;
  readonly registerRow: (eventId: string, element: HTMLButtonElement | null) => void;
}

export const QueueList = ({ items, selectedId, onSelect, registerRow }: QueueListProps) => (
  <ul
    aria-label="Unverified candidates"
    className="divide-y divide-border overflow-hidden rounded-card border border-border bg-surface-1 shadow-ambient"
  >
    {items.map((item) => (
      <QueueRow
        key={item.id}
        item={item}
        isSelected={item.id === selectedId}
        onSelect={onSelect}
        registerRow={registerRow}
      />
    ))}
  </ul>
);
