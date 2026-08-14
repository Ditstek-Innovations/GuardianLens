import { useQuery } from '@tanstack/react-query';

import { Chip, ChipIcon } from '@/components/ui';
import { apiClient } from '@/lib/api/client';
import { unwrapItems } from '@/lib/api/list';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import { configKeys } from '../api/configKeys';
import { ConfigSection } from './ConfigSection';

import type { ListResponse, ModelVersionSummary } from '@/lib/api/types';

const useModelVersionsQuery = () =>
  useQuery({
    queryKey: configKeys.models(),
    queryFn: async ({ signal }) =>
      unwrapItems(
        await apiClient.get<ListResponse<ModelVersionSummary> | ModelVersionSummary[]>(
          '/api/v1/model-versions',
          { signal },
        ),
      ),
  });

/**
 * The gate-G1 evidence trail, visible: which detection models are registered
 * for this tenant, who approved which, and that none is marked deployed.
 * Registration happens through the API (MODEL_INTEGRATION.md) — there is
 * deliberately no create form here; a model is not a row an admin types in.
 */
export const ModelsSection = () => {
  const modelsQuery = useModelVersionsQuery();

  return (
    <ConfigSection
      title="Detection models"
      description="Registered model versions and their approval state (gate G1 evidence trail). The edge agent names one of these on every capture it analyses."
      query={modelsQuery}
      emptyDetail="No model versions are registered. Detection runs as NullDetector — ingestion only — until one is registered and approved (MODEL_INTEGRATION.md)."
    >
      {(models) => (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
              <th scope="col" className="h-10 px-4">Version</th>
              <th scope="col" className="h-10 px-4">Detects</th>
              <th scope="col" className="h-10 px-4">Approval</th>
              <th scope="col" className="h-10 px-4">Deployment</th>
              <th scope="col" className="h-10 px-4">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {models.map((model) => (
              <tr key={model.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                <td className="px-4 py-2 font-mono text-xs text-fg">{model.version}</td>
                <td className="px-4 py-2 text-fg-muted">{model.classes.join(', ')}</td>
                <td className="px-4 py-2">
                  {model.approved_at !== null ? (
                    <Chip variant="ok" icon={<ChipIcon glyph="check" />}>
                      Approved {formatTimestamp(model.approved_at)}
                    </Chip>
                  ) : (
                    <Chip variant="warn" icon={<ChipIcon glyph="alert" />}>
                      Not approved
                    </Chip>
                  )}
                </td>
                <td className="px-4 py-2">
                  {model.deployed_at !== null ? (
                    <Chip variant="ok" icon={<ChipIcon glyph="check" />}>
                      Deployed
                    </Chip>
                  ) : (
                    // Honest state: registration and even approval are NOT
                    // deployment; G1 gates that separately.
                    <Chip variant="neutral" icon={<ChipIcon glyph="circle" />}>
                      Not deployed
                    </Chip>
                  )}
                </td>
                <td className="max-w-md truncate px-4 py-2 text-fg-muted" title={model.notes ?? ''}>
                  {model.notes ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </ConfigSection>
  );
};
