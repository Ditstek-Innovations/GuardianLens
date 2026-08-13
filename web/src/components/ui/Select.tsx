import { forwardRef } from 'react';

import { FIELD_CLASS } from '@/components/ui/Input';
import { cn } from '@/lib/utils/cn';

import type { SelectHTMLAttributes } from 'react';

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...rest }, ref) => (
    <select ref={ref} className={cn(FIELD_CLASS, 'w-auto pr-8', className)} {...rest}>
      {children}
    </select>
  ),
);

Select.displayName = 'Select';
