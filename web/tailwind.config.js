/**
 * Tailwind theme — reads every visual value from styles/tokens.css
 * (FRONTEND_CODING_STANDARDS §12.1, CS-Y-09). Semantic names only: features
 * use bg-surface-2, text-fg-muted, text-danger — never raw palette values
 * (CS-Y-04). Type, radius, elevation and motion are the §12.1 scales and
 * nothing else (CS-Y-10).
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    // §12.1 type scale: 12 / 13 / 14 (base) / 16 / 18 / 22 / 28.
    // tracking-tight is baked in at ≥22 so headings cannot forget it.
    fontSize: {
      xs: ['12px', { lineHeight: '16px' }],
      sm: ['13px', { lineHeight: '18px' }],
      base: ['14px', { lineHeight: '20px' }],
      lg: ['16px', { lineHeight: '24px' }],
      xl: ['18px', { lineHeight: '26px' }],
      '2xl': ['22px', { lineHeight: '28px', letterSpacing: '-0.01em' }],
      '3xl': ['28px', { lineHeight: '34px', letterSpacing: '-0.02em' }],
    },
    // §12.1 radius: controls 8, cards 12, modals 16, chips full.
    // (6 exists solely for the Kbd keycap; see tokens.css.)
    borderRadius: {
      none: '0px',
      sm: '6px',
      DEFAULT: '8px',
      control: '8px',
      md: '8px',
      card: '12px',
      lg: '12px',
      modal: '16px',
      xl: '16px',
      full: '9999px',
    },
    // §12.1 elevation — values are per-theme in tokens.css.
    boxShadow: {
      none: 'none',
      ambient: 'var(--shadow-ambient)',
      glow: 'var(--shadow-glow)',
      modal: 'var(--shadow-modal)',
    },
    // CS-Y-12 motion scale: 120–160ms feedback, 240ms panels.
    transitionDuration: {
      DEFAULT: '160ms',
      120: '120ms',
      160: '160ms',
      240: '240ms',
    },
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: {
          1: 'var(--color-surface-1)',
          2: 'var(--color-surface-2)',
          3: 'var(--color-surface-3)',
        },
        overlay: 'var(--color-overlay)',
        border: {
          DEFAULT: 'var(--color-border)',
          strong: 'var(--color-border-strong)',
        },
        fg: {
          DEFAULT: 'var(--color-fg)',
          muted: 'var(--color-fg-muted)',
          faint: 'var(--color-fg-faint)',
        },
        brand: {
          // 50 is a legacy alias for the subtle tint — prefer brand-subtle.
          50: 'var(--color-brand-subtle)',
          300: 'var(--color-brand-300)',
          400: 'var(--color-brand-400)',
          500: 'var(--color-brand-500)',
          600: 'var(--color-brand-600)',
          700: 'var(--color-brand-700)',
          ink: 'var(--color-brand-ink)',
          subtle: 'var(--color-brand-subtle)',
          'fill-ink': 'var(--color-brand-fill-ink)',
          mark: 'var(--color-brand-mark)',
        },
        ok: {
          DEFAULT: 'var(--color-ok)',
          subtle: 'var(--color-ok-subtle)',
          solid: 'var(--color-ok-solid)',
          'solid-hover': 'var(--color-ok-solid-hover)',
          // Legacy aliases so pre-token classes keep resolving sensibly.
          50: 'var(--color-ok-subtle)',
          700: 'var(--color-ok)',
        },
        warn: {
          DEFAULT: 'var(--color-warn)',
          subtle: 'var(--color-warn-subtle)',
          50: 'var(--color-warn-subtle)',
          700: 'var(--color-warn)',
        },
        danger: {
          DEFAULT: 'var(--color-danger)',
          subtle: 'var(--color-danger-subtle)',
          solid: 'var(--color-danger-solid)',
          'solid-hover': 'var(--color-danger-solid-hover)',
          50: 'var(--color-danger-subtle)',
          500: 'var(--color-danger)',
          600: 'var(--color-danger-solid)',
          700: 'var(--color-danger)',
        },
        // CS-Y-11 — categorical, fixed order, never cycled, never status.
        chart: {
          1: 'var(--color-chart-1)',
          2: 'var(--color-chart-2)',
          3: 'var(--color-chart-3)',
          4: 'var(--color-chart-4)',
          5: 'var(--color-chart-5)',
        },
      },
      scale: { 98: '.98' },
      aria: { invalid: 'invalid="true"' },
      keyframes: {
        shimmer: {
          from: { backgroundPosition: '200% 0' },
          to: { backgroundPosition: '-200% 0' },
        },
        'modal-in': {
          from: { opacity: '0', transform: 'translateY(8px) scale(0.98)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'drawer-in': {
          from: { opacity: '0', transform: 'translateX(-16px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        'toast-in': {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.6s linear infinite',
        'modal-in': 'modal-in 240ms ease-out',
        'fade-in': 'fade-in 160ms ease-out',
        'drawer-in': 'drawer-in 240ms ease-out',
        'toast-in': 'toast-in 160ms ease-out',
      },
    },
  },
  plugins: [],
};
