import { useSitesQuery } from '../api/useConfigQueries';
import { ConfigSection } from './ConfigSection';

export const SitesSection = () => {
  const sitesQuery = useSitesQuery(true);

  return (
    <ConfigSection title="Sites" query={sitesQuery} emptyDetail="No sites are configured.">
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
  );
};
