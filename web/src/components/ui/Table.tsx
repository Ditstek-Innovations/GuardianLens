import { cn } from '@/lib/utils/cn';

import type { ReactNode } from 'react';

/**
 * §12.1 density — review surfaces are compact: 40px rows, hairline dividers,
 * hover surface-2, sticky header when the caller constrains the container
 * height. One table treatment for every list in the product (CS-AD-01).
 */

export interface TableProps {
  readonly children: ReactNode;
  readonly className?: string | undefined;
}

export const Table = ({ children, className }: TableProps) => (
  <div
    className={cn(
      'overflow-auto rounded-card border border-border bg-surface-1 shadow-ambient',
      className,
    )}
  >
    <table className="w-full text-left text-sm">{children}</table>
  </div>
);

export const TableHead = ({ children }: { readonly children: ReactNode }) => (
  <thead className="sticky top-0 z-10 bg-surface-1">
    <tr className="border-b border-border">{children}</tr>
  </thead>
);

export const TableHeadCell = ({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string | undefined;
}) => (
  <th
    scope="col"
    className={cn('h-10 px-4 text-xs font-medium uppercase tracking-wide text-fg-muted', className)}
  >
    {children}
  </th>
);

export const TableBody = ({ children }: { readonly children: ReactNode }) => (
  <tbody className="divide-y divide-border">{children}</tbody>
);

export const TableRow = ({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string | undefined;
}) => (
  <tr className={cn('h-10 transition-colors duration-120 hover:bg-surface-2', className)}>
    {children}
  </tr>
);

export const TableCell = ({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string | undefined;
}) => <td className={cn('px-4 py-2 text-fg', className)}>{children}</td>;
