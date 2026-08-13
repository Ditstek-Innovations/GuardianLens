import { useState } from 'react';

import { Button, Chip, ChipIcon, FormField, Input, Select } from '@/components/ui';

import type { ChipGlyph } from '@/components/ui';

import { MESSAGES } from '@/constants/messages';
import { useToast } from '@/hooks/useToast';

import { useSitesQuery } from '../api/useConfigQueries';
import { useCamerasQuery } from '../api/useConfigQueries';
import { useCreateCamera } from '../api/useCreateCamera';
import { ConfigSection } from './ConfigSection';

import type { FormEvent } from 'react';

interface CameraStatusPresentation {
  readonly label: string;
  readonly glyph: ChipGlyph;
  readonly variant: 'ok' | 'warn' | 'danger' | 'neutral';
}

// TRD §7.4 StreamHealthIndicator — a degraded state must be unmistakable,
// and never colour alone (NFR-ACC-02).
const STATUS_PRESENTATION: Partial<Record<string, CameraStatusPresentation>> = {
  active: { label: 'Active', glyph: 'check', variant: 'ok' },
  degraded: { label: 'Degraded', glyph: 'alert', variant: 'warn' },
  disconnected: { label: 'Disconnected', glyph: 'cross', variant: 'danger' },
  disabled: { label: 'Disabled', glyph: 'circle', variant: 'neutral' },
};

const statusPresentation = (status: string): CameraStatusPresentation =>
  STATUS_PRESENTATION[status] ?? { label: status, glyph: 'dot', variant: 'neutral' };

export const CamerasSection = () => {
  const camerasQuery = useCamerasQuery();
  const sitesQuery = useSitesQuery(true);
  const createCamera = useCreateCamera();
  const [name, setName] = useState('');
  const [siteId, setSiteId] = useState('');
  const [streamUrl, setStreamUrl] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const { showToast } = useToast();

  const effectiveSiteId = siteId !== '' ? siteId : (sitesQuery.data?.[0]?.id ?? '');

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (name.trim() === '' || streamUrl.trim() === '' || effectiveSiteId === '') {
      setFormError('Name, site and stream URL are required.');
      return;
    }
    createCamera.mutate(
      { siteId: effectiveSiteId, name: name.trim(), streamUrl: streamUrl.trim() },
      {
        onSuccess: () => {
          setName('');
          setStreamUrl('');
          setFormError(null);
          // The stream URL is write-only — the API never returns it
          // (TRD §12.4/§12.5). The outcome toast states exactly that
          // (CS-MSG-01, CS-AD-06).
          showToast({ tone: 'success', message: MESSAGES.config.cameraSaved });
        },
        onError: () => {
          showToast({ tone: 'failure', message: MESSAGES.config.cameraSaveFailed });
        },
      },
    );
  };

  const form = (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Register camera"
      className="flex flex-wrap items-end gap-4 rounded-card border border-border bg-surface-1 p-4 shadow-ambient"
    >
      <FormField label="Name" required>
        <Input value={name} onChange={(event) => setName(event.target.value)} className="w-56" />
      </FormField>
      <FormField label="Site" required>
        <Select value={effectiveSiteId} onChange={(event) => setSiteId(event.target.value)}>
          {(sitesQuery.data ?? []).map((site) => (
            <option key={site.id} value={site.id}>
              {site.name}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField
        label="Stream URL (write-only)"
        required
        hint="RTSP URL including credentials. Stored encrypted; never shown again."
        error={formError ?? undefined}
      >
        <Input
          value={streamUrl}
          onChange={(event) => setStreamUrl(event.target.value)}
          autoComplete="off"
          className="w-96"
        />
      </FormField>
      <Button type="submit" isLoading={createCamera.isPending}>
        Register camera
      </Button>
    </form>
  );

  return (
    <ConfigSection
      title="Cameras"
      query={camerasQuery}
      emptyDetail="No cameras are registered."
      actions={form}
    >
      {(cameras) => (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
              <th scope="col" className="h-10 px-4">Name</th>
              <th scope="col" className="h-10 px-4">Location</th>
              <th scope="col" className="h-10 px-4">Stream</th>
              <th scope="col" className="h-10 px-4">Credential</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {cameras.map((camera) => {
              const presentation = statusPresentation(camera.status);
              return (
                <tr key={camera.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                  <td className="px-4 py-2 text-fg">{camera.name}</td>
                  <td className="px-4 py-2 text-fg-muted">{camera.location_description ?? '—'}</td>
                  <td className="px-4 py-2">
                    <Chip variant={presentation.variant} icon={<ChipIcon glyph={presentation.glyph} />}>
                      {presentation.label}
                    </Chip>
                  </td>
                  <td className="px-4 py-2">
                    <Chip variant="neutral" icon={<ChipIcon glyph="lock" />}>
                      Credential stored
                    </Chip>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </ConfigSection>
  );
};
