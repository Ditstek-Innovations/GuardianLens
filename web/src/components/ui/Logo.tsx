/**
 * §12.1 "Brand mark" — THE logo, drawn exactly once: a shield containing a
 * lens. Rounded shield outline (2px stroke, currentColor), an iris circle
 * centred in the shield's upper two-thirds (2px stroke), a filled pupil dot;
 * nothing else, legible at 16px. Colour rides the brand-mark token (400 on
 * dark, 600 on light). It appears in exactly three places — favicon, shell
 * chrome (the sidebar rail, or the top bar where the rail is hidden), auth
 * identity panel — always via this component; public/favicon.svg mirrors the
 * same geometry byte-for-byte (asserted by Logo.test.tsx).
 */

/** Exported so the favicon-mirror test can assert byte-for-byte geometry. */
export const LOGO_SHIELD_PATH = 'M12 2.5 4 5.5v6c0 4.6 3.2 8 8 10 4.8-2 8-5.4 8-10v-6l-8-3Z';
export const LOGO_IRIS = { cx: 12, cy: 10, r: 3.5 } as const;
export const LOGO_PUPIL = { cx: 12, cy: 10, r: 1.25 } as const;

export interface LogoProps {
  /** Rendered square size in px; the geometry stays legible down to 16. */
  readonly size?: number;
}

export const Logo = ({ size = 24 }: LogoProps) => (
  <svg
    aria-hidden="true"
    focusable="false"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    className="shrink-0 text-brand-mark"
  >
    <path d={LOGO_SHIELD_PATH} stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    <circle {...LOGO_IRIS} stroke="currentColor" strokeWidth="2" />
    <circle {...LOGO_PUPIL} fill="currentColor" />
  </svg>
);
