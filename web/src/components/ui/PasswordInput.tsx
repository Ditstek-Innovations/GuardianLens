import { forwardRef, useState } from 'react';

import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/utils/cn';

import type { InputProps } from '@/components/ui/Input';

/**
 * CS-AU-12 (§5.3) — THE password field. A show/hide toggle rendered as an
 * eye / eye-off icon (inline SVG, stroke-based, `currentColor`, no icon font,
 * no external asset) inside the field; `aria-pressed`; an accessible name
 * ("Show password" / "Hide password"); keyboard reachable without trapping
 * focus. Toggling never clears or re-masks the value; paste is never blocked
 * (CS-AU-15).
 *
 * `FormField` labels its direct child by cloning it with `id`,
 * `aria-invalid` and `aria-describedby` (CS-FM-03). This component must
 * therefore forward every injected prop to the real `<input>` — the toggle
 * button is a sibling, outside the label relationship.
 */
export type PasswordInputProps = Omit<InputProps, 'type'>;

const ICON_STROKE = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const;

const EyeIcon = () => (
  <svg aria-hidden="true" focusable="false" width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = () => (
  <svg aria-hidden="true" focusable="false" width="20" height="20" viewBox="0 0 24 24" {...ICON_STROKE}>
    <path d="m3 3 18 18" />
    <path d="M10.6 5.15A10.9 10.9 0 0 1 12 5c6.5 0 10 7 10 7a17.8 17.8 0 0 1-3.05 3.95" />
    <path d="M6.1 6.1A17.1 17.1 0 0 0 2 12s3.5 7 10 7c1.44 0 2.77-.34 3.95-.86" />
    <path d="M9.88 9.88a3 3 0 0 0 4.24 4.24" />
  </svg>
);

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, ...field }, ref) => {
    const [show, setShow] = useState(false);

    return (
      <div className="relative">
        <Input ref={ref} {...field} type={show ? 'text' : 'password'} className={cn('pr-10', className)} />
        <button
          type="button"
          onClick={() => setShow((current) => !current)}
          aria-pressed={show}
          aria-label={show ? 'Hide password' : 'Show password'}
          className={cn(
            'absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-control',
            'text-fg-muted hover:text-fg',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400',
          )}
        >
          {show ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </div>
    );
  },
);

PasswordInput.displayName = 'PasswordInput';
