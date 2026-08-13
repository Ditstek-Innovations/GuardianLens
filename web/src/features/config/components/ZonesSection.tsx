import { useZonesQuery } from '../api/useConfigQueries';
import { ConfigSection } from './ConfigSection';

export const ZonesSection = () => {
  const zonesQuery = useZonesQuery();

  return (
    <ConfigSection title="Zones" query={zonesQuery} emptyDetail="No zones are defined.">
      {(zones) => (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
              <th scope="col" className="h-10 px-4">Name</th>
              <th scope="col" className="h-10 px-4">Camera</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {zones.map((zone) => (
              <tr key={zone.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                <td className="px-4 py-2 text-fg">{zone.name}</td>
                <td className="px-4 py-2 text-fg-muted">{zone.camera_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </ConfigSection>
  );
};
