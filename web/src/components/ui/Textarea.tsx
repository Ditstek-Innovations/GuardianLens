import { forwardRef } from 'react';

import { FIELD_CLASS } from '@/components/ui/Input';
import { cn } from '@/lib/utils/cn';

import type { TextareaHTMLAttributes } from 'react';

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...rest }, ref) => (
    <textarea ref={ref} className={cn(FIELD_CLASS, 'h-auto min-h-20 py-2.5', className)} {...rest} />
  ),
);

Textarea.displayName = 'Textarea';
