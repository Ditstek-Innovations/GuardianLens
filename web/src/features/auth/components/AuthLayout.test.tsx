// §23.3 preamble + CS-AU-14 — the one frame: identity panel, decorative
// self-contained background, and the contrast the tokens must keep.
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AuthLayout } from './AuthLayout';

// ── WCAG 2.x relative-luminance contrast (the 4.5:1 in CS-AU-14) ──────────

type Rgb = readonly [number, number, number];

const hexToRgb = (hex: string): Rgb => {
  const value = hex.replace('#', '');
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ] as const;
};

const channelLuminance = (channel: number): number => {
  const scaled = channel / 255;
  return scaled <= 0.04045 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
};

const luminance = ([r, g, b]: Rgb): number =>
  0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b);

const contrastRatio = (a: Rgb, b: Rgb): number => {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (lighter + 0.05) / (darker + 0.05);
};

/** Source-over composite of `ink` at `alpha` onto an opaque `base`. */
const blend = (ink: Rgb, alpha: number, base: Rgb): Rgb =>
  [0, 1, 2].map((i) => Math.round((ink[i] ?? 0) * alpha + (base[i] ?? 0) * (1 - alpha))) as [
    number,
    number,
    number,
  ];

// Tokens from styles/tokens.css (§12.1, CS-Y-09) — the ones AuthLayout
// paints with, in BOTH themes: dark is the default, light is the `.light`
// variant. Keep these literals in sync with tokens.css.
interface ThemeTokens {
  readonly name: string;
  readonly surface1: Rgb; // identity panel ground
  readonly pageBg: Rgb; // form panel ground (bg token)
  readonly fg: Rgb;
  readonly fgMuted: Rgb;
}

const THEMES: readonly ThemeTokens[] = [
  {
    name: 'dark (default)',
    surface1: hexToRgb('#11161d'),
    pageBg: hexToRgb('#0b0f14'),
    fg: hexToRgb('#e8edf2'),
    fgMuted: hexToRgb('#9aaaba'),
  },
  {
    name: 'light',
    surface1: hexToRgb('#ffffff'),
    pageBg: hexToRgb('#f7f9fb'),
    fg: hexToRgb('#0c1420'),
    fgMuted: hexToRgb('#506070'),
  },
];

// Backdrop ink is brand-500, identical in both themes (§12.1 accent).
const BRAND_500 = hexToRgb('#06b6d4');

// Worst-case backdrop ink: radial gradient peak (0.16) overlapping a polygon
// fill (0.05) — keep in sync with IdentityBackdrop's opacities.
const MAX_BACKDROP_ALPHA = 0.16 + 0.05;

describe('AuthLayout', () => {
  const renderLayout = () =>
    render(
      <AuthLayout title="Sign in" footer={<a href="/signup">Create an account</a>}>
        <p>form goes here</p>
      </AuthLayout>,
    );

  it('renders the h1 from title and titles the document with it (CS-RT-07)', () => {
    renderLayout();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Sign in');
    expect(document.title).toBe('Sign in · Guardian Lens');
  });

  it('renders children and the footer cross-link slot (CS-AU-18)', () => {
    renderLayout();
    expect(screen.getByText('form goes here')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create an account' })).toBeInTheDocument();
  });

  it('ships the background as an aria-hidden inline SVG — no network asset, no animation (CS-AU-14)', () => {
    const { container } = renderLayout();
    const svg = container.querySelector('svg');

    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute('aria-hidden', 'true');
    // Self-contained: nothing in the panel references a URL to fetch.
    expect(container.querySelector('img, picture, video, iframe')).toBeNull();
    expect(container.querySelector('svg image, svg use')).toBeNull();
    // Static: no SMIL animation elements.
    expect(container.querySelector('animate, animateTransform, animateMotion')).toBeNull();
    // The identity panel as a whole is decorative for assistive tech.
    expect(svg?.closest('section')).toHaveAttribute('aria-hidden', 'true');
  });

  it.each(THEMES)(
    'keeps panel text at >= 4.5:1 over the strongest backdrop composite in the $name theme (CS-AU-14, §12.1)',
    ({ surface1, pageBg, fg, fgMuted }) => {
      const worstIdentityGround = blend(BRAND_500, MAX_BACKDROP_ALPHA, surface1);

      // Identity panel: brand line (fg) and product copy (fg-muted).
      expect(contrastRatio(fg, worstIdentityGround)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(fgMuted, worstIdentityGround)).toBeGreaterThanOrEqual(4.5);
      // Form panel ground carries no backdrop, but check its tokens too.
      expect(contrastRatio(fg, pageBg)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(fgMuted, pageBg)).toBeGreaterThanOrEqual(4.5);
    },
  );
});
