import { PageHeading } from "@/components/layout/PageHeading";
import { ROLE } from "@/constants/roles";
import { useAuth } from "@/hooks/useAuth";
import { usePageTitle } from "@/hooks/usePageTitle";

import { AgentsSection } from "./AgentsSection";
import { CamerasSection } from "./CamerasSection";
import { ModelsSection } from "./ModelsSection";
import { RulesSection } from "./RulesSection";
import { SitesSection } from "./SitesSection";
import { ZonesSection } from "./ZonesSection";

/**
 * TRD §10.6 role scoping: sites and cameras are site_admin; zones and rules
 * are safety_manager (site_admin holds "all"). Section visibility shapes
 * navigation only — the API enforces access (CS-SEC-03).
 */
export const ConfigPage = () => {
  usePageTitle("Configuration");
  const { principal } = useAuth();
  const isSiteAdmin =
    principal !== null && principal.roles.includes(ROLE.SITE_ADMIN);

  return (
    <div className="space-y-6">
      <div>
        <PageHeading>Configuration</PageHeading>
        <p className="mt-1 text-sm text-fg-muted">
          Sites, cameras, zones and detection rules for this tenant. Every
          change here is explicit, audited, and takes effect from the next edge
          sync.
        </p>
      </div>
      {isSiteAdmin ? <SitesSection /> : null}
      {isSiteAdmin ? <CamerasSection /> : null}
      {isSiteAdmin ? <AgentsSection /> : null}
      <ZonesSection />
      <RulesSection />
      {isSiteAdmin ? <ModelsSection /> : null}
    </div>
  );
};
