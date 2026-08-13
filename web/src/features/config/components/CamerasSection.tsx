import { useState } from 'react';

import { Button, Chip, ChipIcon, FormField, Input, Modal, Select } from '@/components/ui';

import type { ChipGlyph } from '@/components/ui';

import { MESSAGES } from '@/constants/messages';
import { useToast } from '@/hooks/useToast';

import { useSitesQuery } from '../api/useConfigQueries';
import { useCamerasQuery } from '../api/useConfigQueries';
import { useCreateCamera } from '../api/useCreateCamera';
import { useUpdateCamera } from '../api/useUpdateCamera';
import { ConfigSection } from './ConfigSection';

import type { FormEvent } from 'react';
import type { CameraSummary } from '@/lib/api/types';

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

interface PendingCamera {
  readonly siteId: string;
  readonly siteName: string;
  readonly name: string;
  readonly streamUrl: string;
  readonly locationDescription: string | null;
  readonly streamProfile: 'primary' | 'secondary';
  readonly sampleRateFps: number;
}

/**
 * CS-AD-06 — the stored credential is never shown; replacement is a fresh
 * write-only submit. The dialog collects the new URL and confirms in one
 * step; the previous credential stays in force until the server confirms.
 */
const ReplaceCredentialDialog = ({
  camera,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly camera: CameraSummary;
  readonly isSubmitting: boolean;
  readonly onConfirm: (streamUrl: string) => void;
  readonly onCancel: () => void;
}) => {
  const [streamUrl, setStreamUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (streamUrl.trim() === '') {
      setError('The new stream URL is required.');
      return;
    }
    setError(null);
    onConfirm(streamUrl.trim());
  };

  return (
    <Modal title="Replace credential" onClose={onCancel}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <p className="text-sm text-fg">
          A new stream credential for “{camera.name}” replaces the stored one. The current
          credential cannot be shown — it is sealed and the server cannot read it back.
        </p>
        <FormField
          label="New stream URL (write-only)"
          required
          hint="RTSP URL including credentials. Sealed on save; never shown again."
          error={error ?? undefined}
        >
          <Input
            value={streamUrl}
            onChange={(event) => setStreamUrl(event.target.value)}
            autoComplete="off"
          />
        </FormField>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isSubmitting}>
            Replace credential
          </Button>
        </div>
      </form>
    </Modal>
  );
};

/**
 * CS-AD-03 — disabling a camera changes what is watched; the confirmation
 * names the effect. Enabling is symmetrical.
 */
const CameraStatusDialog = ({
  camera,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly camera: CameraSummary;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => {
  const isDisabling = camera.status !== 'disabled';
  const title = isDisabling ? 'Disable camera' : 'Enable camera';
  return (
    <Modal title={title} onClose={onCancel}>
      <div className="space-y-4">
        <p className="text-sm text-fg">
          {isDisabling
            ? `“${camera.name}” will no longer be watched from the next edge sync. Its recorded events and history remain.`
            : `“${camera.name}” will be watched again from the next edge sync, under its zones' active rules.`}
        </p>
        <p className="text-xs text-fg-muted">The change is audited under your name.</p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant={isDisabling ? 'danger' : 'primary'}
            onClick={onConfirm}
            isLoading={isSubmitting}
          >
            {title}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

/**
 * CS-AD-03 — adding a camera is an explicit, confirmed submit that names in
 * plain words what will change and where. The stream URL is deliberately
 * NOT restated here — it carries credentials (BR-S-03).
 */
const RegisterCameraDialog = ({
  pending,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly pending: PendingCamera;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => (
  <Modal title="Register camera" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        “{pending.name}” will be added at {pending.siteName}. Its stream credential is sealed on
        save and never shown again.
      </p>
      <p className="text-xs text-fg-muted">
        Nothing on this camera is monitored until a detection rule is explicitly activated
        (BR-001). The registration is audited.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} isLoading={isSubmitting}>
          Register camera
        </Button>
      </div>
    </div>
  </Modal>
);

export const CamerasSection = () => {
  const camerasQuery = useCamerasQuery();
  const sitesQuery = useSitesQuery(true);
  const createCamera = useCreateCamera();
  const updateCamera = useUpdateCamera();
  const [name, setName] = useState('');
  const [siteId, setSiteId] = useState('');
  const [streamUrl, setStreamUrl] = useState('');
  const [location, setLocation] = useState('');
  const [streamProfile, setStreamProfile] = useState<'primary' | 'secondary'>('secondary');
  const [sampleRateFps, setSampleRateFps] = useState('2');
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingCamera | null>(null);
  const [replaceTarget, setReplaceTarget] = useState<CameraSummary | null>(null);
  const [statusTarget, setStatusTarget] = useState<CameraSummary | null>(null);
  const { showToast } = useToast();

  const sites = sitesQuery.data ?? [];
  const effectiveSiteId = siteId !== '' ? siteId : (sites[0]?.id ?? '');

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const site = sites.find((candidate) => candidate.id === effectiveSiteId);
    const parsedFps = Number(sampleRateFps);
    if (name.trim() === '' || streamUrl.trim() === '' || site === undefined) {
      setFormError('Name, site and stream URL are required.');
      return;
    }
    if (Number.isNaN(parsedFps) || parsedFps <= 0 || parsedFps > 30) {
      setFormError('Sample rate must be a number greater than 0 and at most 30 fps.');
      return;
    }
    setFormError(null);
    setPending({
      siteId: site.id,
      siteName: site.name,
      name: name.trim(),
      streamUrl: streamUrl.trim(),
      locationDescription: location.trim() === '' ? null : location.trim(),
      streamProfile,
      sampleRateFps: parsedFps,
    });
  };

  const handleConfirm = (): void => {
    if (pending === null) return;
    createCamera.mutate(
      {
        siteId: pending.siteId,
        name: pending.name,
        streamUrl: pending.streamUrl,
        locationDescription: pending.locationDescription,
        streamProfile: pending.streamProfile,
        sampleRateFps: pending.sampleRateFps,
      },
      {
        onSuccess: () => {
          setPending(null);
          setName('');
          setStreamUrl('');
          setLocation('');
          setStreamProfile('secondary');
          setSampleRateFps('2');
          // The stream URL is write-only — the API never returns it
          // (TRD §12.4/§12.5). The outcome toast states exactly that
          // (CS-MSG-01, CS-AD-06).
          showToast({ tone: 'success', message: MESSAGES.config.cameraSaved });
        },
        onError: () => {
          // The dialog stays open for retry (CS-MSG-05); nothing was stored.
          showToast({ tone: 'failure', message: MESSAGES.config.cameraSaveFailed });
        },
      },
    );
  };

  const handleReplaceCredential = (newStreamUrl: string): void => {
    if (replaceTarget === null) return;
    updateCamera.mutate(
      { cameraId: replaceTarget.id, streamUrl: newStreamUrl },
      {
        onSuccess: () => {
          setReplaceTarget(null);
          showToast({ tone: 'success', message: MESSAGES.config.cameraCredentialReplaced });
        },
        onError: () => {
          showToast({
            tone: 'failure',
            message: MESSAGES.config.cameraCredentialReplaceFailed,
          });
        },
      },
    );
  };

  const handleStatusChange = (): void => {
    if (statusTarget === null) return;
    const willDisable = statusTarget.status !== 'disabled';
    const cameraName = statusTarget.name;
    updateCamera.mutate(
      { cameraId: statusTarget.id, status: willDisable ? 'disabled' : 'active' },
      {
        onSuccess: () => {
          setStatusTarget(null);
          showToast({
            tone: 'success',
            message: willDisable
              ? MESSAGES.config.cameraDisabled(cameraName)
              : MESSAGES.config.cameraEnabled(cameraName),
          });
        },
        onError: () => {
          showToast({ tone: 'failure', message: MESSAGES.config.cameraStatusChangeFailed });
        },
      },
    );
  };

  const form = (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Register camera"
      className="grid gap-4 lg:grid-cols-12"
    >
      <FormField label="Name" required className="lg:col-span-3">
        <Input value={name} onChange={(event) => setName(event.target.value)} />
      </FormField>
      <FormField label="Site" required className="lg:col-span-3">
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
        className="lg:col-span-6"
      >
        <Input
          value={streamUrl}
          onChange={(event) => setStreamUrl(event.target.value)}
          autoComplete="off"
        />
      </FormField>
      <FormField
        label="Location"
        hint="Where the camera physically is, e.g. “North wall, dock 3”."
        className="lg:col-span-6"
      >
        <Input value={location} onChange={(event) => setLocation(event.target.value)} />
      </FormField>
      <FormField
        label="Stream profile"
        required
        hint="Secondary (SD) is far cheaper to decode; safety rules rarely need HD."
        className="lg:col-span-3"
      >
        <Select
          value={streamProfile}
          onChange={(event) => setStreamProfile(event.target.value as 'primary' | 'secondary')}
        >
          <option value="secondary">Secondary (SD)</option>
          <option value="primary">Primary (HD)</option>
        </Select>
      </FormField>
      <FormField
        label="Sample rate (fps)"
        required
        hint="Frames sampled per second, up to 30. Safety rules rarely need more than 2."
        className="lg:col-span-3"
      >
        <Input
          type="number"
          min={0.1}
          max={30}
          step={0.5}
          inputMode="decimal"
          value={sampleRateFps}
          onChange={(event) => setSampleRateFps(event.target.value)}
        />
      </FormField>
      <div className="flex items-end justify-end lg:col-span-12">
        <Button type="submit" isLoading={createCamera.isPending}>
          Register camera
        </Button>
      </div>
    </form>
  );

  return (
    <>
    <ConfigSection
      title="Cameras"
      description="Streams the edge agent watches. The credential is sealed on save and never shown or returned again."
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
              <th scope="col" className="h-10 px-4">Profile</th>
              <th scope="col" className="h-10 px-4">Sample rate</th>
              <th scope="col" className="h-10 px-4">Stream</th>
              <th scope="col" className="h-10 px-4">Credential</th>
              <th scope="col" className="h-10 px-4">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {cameras.map((camera) => {
              const presentation = statusPresentation(camera.status);
              return (
                <tr key={camera.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                  <td className="px-4 py-2 text-fg">{camera.name}</td>
                  <td className="px-4 py-2 text-fg-muted">{camera.location_description ?? '—'}</td>
                  <td className="px-4 py-2 text-fg-muted">
                    {camera.stream_profile === 'primary' ? 'Primary (HD)' : 'Secondary (SD)'}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-fg-muted">{camera.sample_rate_fps} fps</td>
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
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setReplaceTarget(camera)}
                      >
                        Replace credential
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setStatusTarget(camera)}
                      >
                        {camera.status === 'disabled' ? 'Enable' : 'Disable'}
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </ConfigSection>
    {pending !== null ? (
      <RegisterCameraDialog
        pending={pending}
        isSubmitting={createCamera.isPending}
        onConfirm={handleConfirm}
        onCancel={() => setPending(null)}
      />
    ) : null}
    {replaceTarget !== null ? (
      <ReplaceCredentialDialog
        camera={replaceTarget}
        isSubmitting={updateCamera.isPending}
        onConfirm={handleReplaceCredential}
        onCancel={() => setReplaceTarget(null)}
      />
    ) : null}
    {statusTarget !== null ? (
      <CameraStatusDialog
        camera={statusTarget}
        isSubmitting={updateCamera.isPending}
        onConfirm={handleStatusChange}
        onCancel={() => setStatusTarget(null)}
      />
    ) : null}
    </>
  );
};
