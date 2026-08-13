import { assertNever } from '@/lib/utils/assertNever';

/**
 * The tiny inline glyphs a Chip carries (NFR-ACC-02 — icon + text, never
 * colour alone). Stroke-based, currentColor, 12px — no icon font, no
 * external asset, domain-blind (CS-U-02).
 */
export type ChipGlyph = 'check' | 'cross' | 'alert' | 'circle' | 'dot' | 'lock';

const GLYPH_PROPS = {
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

export interface ChipIconProps {
  readonly glyph: ChipGlyph;
}

export const ChipIcon = ({ glyph }: ChipIconProps) => {
  switch (glyph) {
    case 'check':
      return (
        <svg {...GLYPH_PROPS}>
          <path d="m4 12.5 5.5 5.5L20 6.5" />
        </svg>
      );
    case 'cross':
      return (
        <svg {...GLYPH_PROPS}>
          <path d="m5 5 14 14M19 5 5 19" />
        </svg>
      );
    case 'alert':
      return (
        <svg {...GLYPH_PROPS}>
          <path d="M12 3 2.5 20h19L12 3Z" />
          <path d="M12 10v4" />
          <path d="M12 17h.01" />
        </svg>
      );
    case 'circle':
      return (
        <svg {...GLYPH_PROPS}>
          <circle cx="12" cy="12" r="8.5" />
        </svg>
      );
    case 'dot':
      return (
        <svg {...GLYPH_PROPS}>
          <circle cx="12" cy="12" r="5" fill="currentColor" stroke="none" />
        </svg>
      );
    case 'lock':
      return (
        <svg {...GLYPH_PROPS}>
          <rect x="5" y="10.5" width="14" height="9.5" rx="2" />
          <path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3" />
        </svg>
      );
    default:
      return assertNever(glyph);
  }
};
