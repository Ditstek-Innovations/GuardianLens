import { useState } from 'react';

import { Button, FormField, Input, Modal } from '@/components/ui';
import { MESSAGES } from '@/constants/messages';
import { useToast } from '@/hooks/useToast';

import { useSitesQuery } from '../api/useConfigQueries';
import { useCreateSite } from '../api/useCreateSite';
import { ConfigSection } from './ConfigSection';

import type { FormEvent } from 'react';

/** The operator's own zone — a real value from the machine, never a guess. */
const browserTimezone = (): string => Intl.DateTimeFormat().resolvedOptions().timeZone;

interface PendingSite {
  readonly name: string;
  readonly timezone: string;
}

/** CS-AD-03 — a new site widens what this tenant can watch; confirm it. */
const CreateSiteDialog = ({
  pending,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly pending: PendingSite;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => (
  <Modal title="Create site" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        “{pending.name}” will be created with timezone {pending.timezone}. You receive site admin
        there, recorded under your name.
      </p>
      <p className="text-xs text-fg-muted">
        Cameras, zones and reports at the site are scoped to it. Nothing is monitored until a rule
        is explicitly activated (BR-001). The creation is audited.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} isLoading={isSubmitting}>
          Create site
        </Button>
      </div>
    </div>
  </Modal>
);

export const SitesSection = () => {
  const sitesQuery = useSitesQuery(true);
  const createSite = useCreateSite();
  const { showToast } = useToast();
  const [name, setName] = useState('');
  const [timezone, setTimezone] = useState(browserTimezone);
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingSite | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedZone = timezone.trim();
    if (trimmedName === '' || trimmedZone === '') {
      setFormError('Name and timezone are required.');
      return;
    }
    setFormError(null);
    setPending({ name: trimmedName, timezone: trimmedZone });
  };

  const handleConfirm = (): void => {
    if (pending === null) return;
    createSite.mutate(pending, {
      onSuccess: () => {
        setPending(null);
        setName('');
        showToast({ tone: 'success', message: MESSAGES.config.siteSaved });
      },
      onError: () => {
        // The dialog stays open for retry (CS-MSG-05); nothing was stored.
        showToast({ tone: 'failure', message: MESSAGES.config.siteSaveFailed });
      },
    });
  };

  const form = (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Create site"
      className="grid gap-4 lg:grid-cols-12"
    >
      <FormField label="Name" required error={formError ?? undefined} className="lg:col-span-5">
        <Input value={name} onChange={(event) => setName(event.target.value)} />
      </FormField>
      <FormField
        label="Timezone"
        required
        hint="IANA zone, e.g. Asia/Kolkata — report periods and timestamps render in site-local time."
        className="lg:col-span-4"
      >
        <Input value={timezone} onChange={(event) => setTimezone(event.target.value)} />
      </FormField>
      <div className="flex items-start justify-end pt-6 lg:col-span-3">
        <Button type="submit" isLoading={createSite.isPending}>
          Create site
        </Button>
      </div>
    </form>
  );

  return (
    <>
      <ConfigSection
        title="Sites"
        description="Physical locations this tenant monitors. Cameras, zones and reports are scoped to a site."
        query={sitesQuery}
        emptyDetail="No sites are configured."
        actions={form}
        actionLabel="Add site"
      >
        {(sites) => (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
                <th scope="col" className="h-10 px-4">Name</th>
                <th scope="col" className="h-10 px-4">Timezone</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sites.map((site) => (
                <tr key={site.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                  <td className="px-4 py-2 text-fg">{site.name}</td>
                  <td className="px-4 py-2 text-fg-muted">{site.timezone}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ConfigSection>
      {pending !== null ? (
        <CreateSiteDialog
          pending={pending}
          isSubmitting={createSite.isPending}
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      ) : null}
    </>
  );
};
