import { cn } from '@/lib/utils/cn';

export interface ToggleProps {
  readonly checked: boolean;
  readonly onChange: (checked: boolean) => void;
  readonly label: string;
  readonly disabled?: boolean;
}

/** §12.1 — an accessible switch: real button, role="switch", brand fill when on. */
export const Toggle = ({ checked, onChange, label, disabled = false }: ToggleProps) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={cn(
      'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-120',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
      checked ? 'bg-brand-500' : 'bg-surface-3',
      disabled && 'cursor-not-allowed opacity-50',
    )}
  >
    <span
      aria-hidden="true"
      className={cn(
        'inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-120',
        checked ? 'translate-x-6' : 'translate-x-1',
      )}
    />
  </button>
);
