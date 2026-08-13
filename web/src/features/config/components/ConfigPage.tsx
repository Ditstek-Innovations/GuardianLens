import { PageHeading } from '@/components/layout/PageHeading';
import { ROLE } from '@/constants/roles';
import { useAuth } from '@/hooks/useAuth';
import { usePageTitle } from '@/hooks/usePageTitle';

import { CamerasSection } from './CamerasSection';
import { RulesSection } from './RulesSection';
import { SitesSection } from './SitesSection';
import { ZonesSection } from './ZonesSection';

/**
 * TRD §10.6 role scoping: sites and cameras are site_admin; zones and rules
 * are safety_manager (site_admin holds "all"). Section visibility shapes
 * navigation only — the API enforces access (CS-SEC-03).
 */
export const ConfigPage = () => {
  usePageTitle('Configuration');
  const { principal } = useAuth();
  const isSiteAdmin = principal !== null && principal.roles.includes(ROLE.SITE_ADMIN);

  return (
    <div className="space-y-8">
      <PageHeading>Configuration</PageHeading>
      {isSiteAdmin ? <SitesSection /> : null}
      {isSiteAdmin ? <CamerasSection /> : null}
      <ZonesSection />
      <RulesSection />
    </div>
  );
};
