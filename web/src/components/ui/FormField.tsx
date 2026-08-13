import { cloneElement, useId } from 'react';

import { cn } from '@/lib/utils/cn';

import type { ReactElement } from 'react';

interface FieldControlProps {
  id?: string | undefined;
  required?: boolean | undefined;
  'aria-invalid'?: boolean | undefined;
  'aria-describedby'?: string | undefined;
}

export interface FormFieldProps {
  readonly label: string;
  readonly error?: string | undefined;
  readonly hint?: string | undefined;
  readonly required?: boolean;
  /** Layout hook for the wrapper (grid column spans, widths) — nothing visual. */
  readonly className?: string | undefined;
  readonly children: ReactElement<FieldControlProps>;
}

/**
 * CS-FM-03 / CS-FM-09 — label association, error rendering (`aria-invalid` +
 * `aria-describedby`, error as text) and required-marking implemented once.
 */
export const FormField = ({
  label,
  error,
  hint,
  required = false,
  className,
  children,
}: FormFieldProps) => {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy =
    [error !== undefined ? errorId : null, hint !== undefined ? hintId : null]
      .filter((part): part is string => part !== null)
      .join(' ') || undefined;

  const control = cloneElement(children, {
    id,
    required,
    'aria-invalid': error !== undefined ? true : undefined,
    'aria-describedby': describedBy,
  });

  return (
    <div className={cn('space-y-1', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-fg">
        {label}
        {required ? <span aria-hidden="true"> *</span> : null}
      </label>
      {control}
      {hint !== undefined ? (
        <p id={hintId} className="text-xs text-fg-muted">
          {hint}
        </p>
      ) : null}
      {error !== undefined ? (
        <p id={errorId} role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
};
