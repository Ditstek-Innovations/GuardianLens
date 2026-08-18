import { PageHeading } from '@/components/layout/PageHeading';
import {
  EmptyState,
  ErrorState,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeadCell,
  TableRow,
} from '@/components/ui';
import { usePageTitle } from '@/hooks/usePageTitle';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import { useAuditQuery } from '../api/useAuditQuery';

import type { ReactNode } from 'react';

/** Read-only by construction — audit entries are append-only (BR-AU-01). */
export const AuditPage = () => {
  usePageTitle('Audit log');
  const auditQuery = useAuditQuery();

  let content: ReactNode;
  if (auditQuery.isPending) {
    // CS-Y-13 — skeleton rows in the table frame; no shift on resolve.
    content = (
      <div
        aria-label="Loading audit log"
        className="space-y-2 rounded-card border border-border bg-surface-1 p-4 shadow-ambient"
      >
        <p className="sr-only">Loading audit log…</p>
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-2/3" />
      </div>
    );
  } else if (auditQuery.isError || auditQuery.data === undefined) {
    content = (
      <ErrorState
        title="The audit log could not be loaded."
        detail="GET /api/v1/audit is a [V1] endpoint (TRD §10.6) — the MVP control plane may not serve it yet."
        onRetry={() => void auditQuery.refetch()}
      />
    );
  } else if (auditQuery.data.length === 0) {
    content = <EmptyState title="No audit entries" detail="Nothing has been recorded yet." />;
  } else {
    content = (
      <Table>
        <TableHead>
          <TableHeadCell>When</TableHeadCell>
          <TableHeadCell>Actor</TableHeadCell>
          <TableHeadCell>Action</TableHeadCell>
          <TableHeadCell>Entity</TableHeadCell>
        </TableHead>
        <TableBody>
          {auditQuery.data.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className="tabular-nums">
                {entry.created_at !== undefined ? formatTimestamp(entry.created_at) : '—'}
              </TableCell>
              <TableCell>{entry.actor?.full_name ?? '—'}</TableCell>
              <TableCell className="text-fg-muted">{entry.action}</TableCell>
              <TableCell className="text-fg-muted">
                {entry.entity_type ?? '—'} {entry.entity_id ?? ''}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  }

  return (
    <section aria-label="Audit log" className="space-y-4">
      <PageHeading>Audit log</PageHeading>
      <p className="text-sm text-fg-muted">
        Append-only record of configuration and decision history (BR-AU-01). Read-only.
      </p>
      {content}
    </section>
  );
};
