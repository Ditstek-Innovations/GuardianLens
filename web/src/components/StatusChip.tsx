import { Chip } from '@/components/ui';
import { EVENT_STATUS } from '@/constants/events';
import { assertNever } from '@/lib/utils/assertNever';

import type { ReactNode } from 'react';
import type { ChipVariant } from '@/components/ui';
import type { EventStatus } from '@/constants/events';

interface StatusPresentation {
  readonly label: string;
  readonly variant: ChipVariant;
  readonly icon: ReactNode;
}

// Inline stroke icons, currentColor, 12px — no icon font, no external asset.
const ICON_PROPS = {
  'aria-hidden': true,
  focusable: false,
  width: 12,
  height: 12,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const;

const DotIcon = () => (
  <svg {...ICON_PROPS}>
    <circle cx="12" cy="12" r="5" fill="currentColor" stroke="none" />
  </svg>
);

const CheckIcon = () => (
  <svg {...ICON_PROPS}>
    <path d="m4 12.5 5.5 5.5L20 6.5" />
  </svg>
);

const PencilIcon = () => (
  <svg {...ICON_PROPS}>
    <path d="M17 3.5 20.5 7 8 19.5 3.5 20.5 4.5 16Z" />
  </svg>
);

const CrossIcon = () => (
  <svg {...ICON_PROPS}>
    <path d="m5 5 14 14M19 5 5 19" />
  </svg>
);

const SlashCircleIcon = () => (
  <svg {...ICON_PROPS}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="m6.5 17.5 11-11" />
  </svg>
);

// Domain-aware, so it lives outside components/ui (CS-U-02).
// NFR-ACC-02 — text + icon for every status; colour is never the sole signal.
const presentationFor = (status: EventStatus): StatusPresentation => {
  switch (status) {
    case EVENT_STATUS.UNVERIFIED:
      return { label: 'Unverified', variant: 'warn', icon: <DotIcon /> };
    case EVENT_STATUS.ACCEPTED:
      return { label: 'Accepted', variant: 'ok', icon: <CheckIcon /> };
    case EVENT_STATUS.CORRECTED:
      return { label: 'Corrected', variant: 'brand', icon: <PencilIcon /> };
    case EVENT_STATUS.REJECTED:
      return { label: 'Rejected', variant: 'danger', icon: <CrossIcon /> };
    case EVENT_STATUS.EXPIRED:
      return { label: 'Expired', variant: 'neutral', icon: <SlashCircleIcon /> };
    default:
      return assertNever(status);
  }
};

export interface StatusChipProps {
  readonly status: EventStatus;
}

export const StatusChip = ({ status }: StatusChipProps) => {
  const presentation = presentationFor(status);
  return (
    <Chip variant={presentation.variant} icon={presentation.icon}>
      {presentation.label}
    </Chip>
  );
};
