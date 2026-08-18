import { Logo } from '@/components/ui';
import { usePageTitle } from '@/hooks/usePageTitle';

import type { ReactNode } from 'react';

// FRONTEND_CODING_STANDARDS §23.3 — the ONE frame for SCR-1…SCR-1c. Each
// auth screen contributes only its form (children) and its cross-links
// (footer, CS-AU-18); the frame, identity panel and background treatment
// live here exactly once. Two auth screens that disagree about their frame
// are two different applications on adjacent URLs.

export interface AuthLayoutProps {
  readonly title: string;
  readonly children: ReactNode;
  /** CS-AU-18 — links to OTHER AUTH SCREENS only; never into the app. */
  readonly footer?: ReactNode | undefined;
}

/**
 * CS-AU-14 — decorative, self-contained background: an inline SVG shipped in
 * the bundle. A soft radial gradient in the brand hue plus a few translucent
 * stroked polygons echoing the product's zone polygons. No photograph, no
 * person, no evidence frame (CS-AU-02), no network asset, and no animation —
 * a static image trivially satisfies `prefers-reduced-motion`.
 *
 * Contrast: the strongest composite ink is brand-500 at ~0.21 alpha over
 * surface-1 (gradient 0.16 + polygon fill 0.05). AuthLayout.test.tsx computes
 * the WCAG ratio of fg / fg-muted against that worst case IN BOTH THEMES
 * (§12.1 tokens) and asserts ≥ 4.5:1 — keep the test in sync when changing
 * these opacities or the surface/ink tokens.
 */
const IdentityBackdrop = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    className="pointer-events-none absolute inset-0 h-full w-full text-brand-500"
    viewBox="0 0 640 480"
    preserveAspectRatio="xMidYMid slice"
    fill="none"
  >
    <defs>
      <radialGradient id="gl-auth-backdrop-glow" cx="30%" cy="22%" r="80%">
        <stop offset="0%" stopColor="currentColor" stopOpacity="0.16" />
        <stop offset="55%" stopColor="currentColor" stopOpacity="0.05" />
        <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
      </radialGradient>
    </defs>
    <rect width="640" height="480" fill="url(#gl-auth-backdrop-glow)" />
    <polygon
      points="40,340 190,300 252,420 92,462"
      stroke="currentColor"
      strokeOpacity="0.18"
      strokeWidth="2"
      fill="currentColor"
      fillOpacity="0.05"
    />
    <polygon
      points="420,58 592,92 560,222 402,190"
      stroke="currentColor"
      strokeOpacity="0.14"
      strokeWidth="2"
      fill="currentColor"
      fillOpacity="0.04"
    />
    <polygon
      points="298,242 400,270 372,362 262,330"
      stroke="currentColor"
      strokeOpacity="0.1"
      strokeWidth="1.5"
      fill="currentColor"
      fillOpacity="0.03"
    />
  </svg>
);

export const AuthLayout = ({ title, children, footer }: AuthLayoutProps) => {
  // CS-RT-07 — every auth screen titles the document from the same prop that
  // renders its h1, so tab and page can never disagree.
  usePageTitle(title);

  return (
    // CS-AU-01 — outside AppShell, no navigation. Two panels at md+; below
    // md the identity panel collapses to a compact header so the form is
    // never below the fold on a phone (§23.3).
    <main className="flex min-h-screen flex-col bg-bg md:grid md:grid-cols-2">
      <section
        aria-hidden="true"
        className="relative overflow-hidden border-b border-border bg-surface-1 px-6 py-4 md:flex md:flex-col md:justify-center md:border-b-0 md:border-r md:px-12 md:py-10"
      >
        <IdentityBackdrop />
        <div className="relative">
          <p className="flex items-center gap-2.5 text-xl font-semibold tracking-tight text-fg">
            <Logo size={26} />
            Guardian Lens
          </p>
          <div className="hidden md:block">
            <p className="mt-4 max-w-sm text-fg-muted">
              Human-verified safety and compliance monitoring for the cameras
              you already own.
            </p>
            {/* CS-AU-02 — informational only: no controls, no second form, no
                imagery of workers, no evidence frame. */}
            <ul className="mt-6 max-w-sm space-y-3 text-sm text-fg-muted">
              <li className="flex gap-2">
                <span aria-hidden="true">•</span>
                Nothing is recorded until a person confirms it.
              </li>
              <li className="flex gap-2">
                <span aria-hidden="true">•</span>
                Nothing outside a configured safety rule is watched at all.
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="flex flex-1 items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold text-fg">{title}</h1>
          <div className="mt-4">{children}</div>
          {footer !== undefined ? (
            <div className="mt-6 border-t border-border pt-4 text-sm">{footer}</div>
          ) : null}
        </div>
      </section>
    </main>
  );
};
