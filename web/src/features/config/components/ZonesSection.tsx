import { useState } from 'react';

import { Button, FormField, Input, Modal, Select } from '@/components/ui';
import { MESSAGES } from '@/constants/messages';
import { ROLE } from '@/constants/roles';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';

import { useCamerasQuery, useSitesQuery, useZonesQuery } from '../api/useConfigQueries';
import { useCreateZone } from '../api/useCreateZone';
import { ConfigSection } from './ConfigSection';

import type { FormEvent } from 'react';

/**
 * SCR-8 `[MVP]` minimal — the zone is the camera's full frame. Drawing a
 * finer polygon over a reference frame is a refinement, not a prerequisite:
 * a full-frame zone plus an inactive-by-default rule already expresses
 * "watch this camera for this rule" honestly.
 */
const FULL_FRAME_POLYGON: readonly (readonly [number, number])[] = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

interface PendingZone {
  readonly cameraId: string;
  readonly cameraName: string;
  readonly name: string;
}

/** CS-AD-03 — changing what can be watched is an explicit, confirmed submit. */
const CreateZoneDialog = ({
  pending,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly pending: PendingZone;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => (
  <Modal title="Create zone" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        “{pending.name}” will cover the full frame of camera {pending.cameraName}. Detection rules
        can then be attached to it.
      </p>
      <p className="text-xs text-fg-muted">
        Nothing in this zone is monitored until a rule is explicitly activated (BR-001). The change
        is audited and reaches the edge on its next sync.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} isLoading={isSubmitting}>
          Create zone
        </Button>
      </div>
    </div>
  </Modal>
);

export const ZonesSection = () => {
  const { principal } = useAuth();
  const zonesQuery = useZonesQuery();
  // Cameras and sites are site_admin-scoped (TRD §10.6); the create form is
  // therefore admin-only, and the camera-name column falls back to the raw
  // id for the roles that cannot enumerate cameras.
  const isSiteAdmin = principal !== null && principal.roles.includes(ROLE.SITE_ADMIN);
  const camerasQuery = useCamerasQuery(isSiteAdmin);
  const sitesQuery = useSitesQuery(isSiteAdmin);
  const createZone = useCreateZone();
  const { showToast } = useToast();
  const [name, setName] = useState('');
  const [cameraId, setCameraId] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingZone | null>(null);

  const cameras = camerasQuery.data ?? [];
  const siteName = (siteId: string): string | null =>
    (sitesQuery.data ?? []).find((site) => site.id === siteId)?.name ?? null;
  const cameraLabel = (camera: { name: string; site_id: string }): string => {
    const site = siteName(camera.site_id);
    return site !== null ? `${camera.name} — ${site}` : camera.name;
  };
  const effectiveCameraId = cameraId !== '' ? cameraId : (cameras[0]?.id ?? '');

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmed = name.trim();
    const camera = cameras.find((candidate) => candidate.id === effectiveCameraId);
    if (trimmed === '' || camera === undefined) {
      setFormError('Name and camera are required.');
      return;
    }
    setFormError(null);
    setPending({ cameraId: camera.id, cameraName: cameraLabel(camera), name: trimmed });
  };

  const handleConfirm = (): void => {
    if (pending === null) return;
    createZone.mutate(
      { cameraId: pending.cameraId, name: pending.name, polygon: FULL_FRAME_POLYGON },
      {
        onSuccess: () => {
          setPending(null);
          setName('');
          showToast({ tone: 'success', message: MESSAGES.config.zoneSaved });
        },
        onError: () => {
          // The dialog stays open for retry (CS-MSG-05); nothing was stored.
          showToast({ tone: 'failure', message: MESSAGES.config.zoneSaveFailed });
        },
      },
    );
  };

  const form = isSiteAdmin ? (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Create zone"
      className="grid gap-4 lg:grid-cols-12"
    >
      <FormField label="Name" required error={formError ?? undefined} className="lg:col-span-4">
        <Input value={name} onChange={(event) => setName(event.target.value)} />
      </FormField>
      <FormField
        label="Camera"
        required
        hint="The zone covers the camera's full frame at MVP."
        className="lg:col-span-5"
      >
        <Select value={effectiveCameraId} onChange={(event) => setCameraId(event.target.value)}>
          {cameras.map((camera) => (
            <option key={camera.id} value={camera.id}>
              {cameraLabel(camera)}
            </option>
          ))}
        </Select>
      </FormField>
      <div className="flex items-start justify-end pt-6 lg:col-span-3">
        <Button type="submit" isLoading={createZone.isPending}>
          Create zone
        </Button>
      </div>
    </form>
  ) : undefined;

  return (
    <>
      <ConfigSection
        title="Zones"
        description="Regions within a camera's view that detection rules apply to."
        query={zonesQuery}
        emptyDetail="No zones are defined."
        {...(form !== undefined ? { actions: form } : {})}
      >
        {(zones) => (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
                <th scope="col" className="h-10 px-4">Name</th>
                <th scope="col" className="h-10 px-4">Camera</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {zones.map((zone) => {
                const camera = cameras.find((candidate) => candidate.id === zone.camera_id);
                return (
                  <tr key={zone.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                    <td className="px-4 py-2 text-fg">{zone.name}</td>
                    <td className="px-4 py-2 text-fg-muted">
                      {camera !== undefined ? cameraLabel(camera) : zone.camera_id}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </ConfigSection>
      {pending !== null ? (
        <CreateZoneDialog
          pending={pending}
          isSubmitting={createZone.isPending}
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      ) : null}
    </>
  );
};
