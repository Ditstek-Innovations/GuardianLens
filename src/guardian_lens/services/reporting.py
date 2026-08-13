"""ReportingService — MOD-9 basic: read-only aggregation over verified
records, always with coverage context.

Two mandates shape every response:

  * basis is verified_events_only, enforced by the repository-level
    filter, so no caller can produce a count containing rejections
    (BR-R-01); and
  * coverage_gaps_minutes is always present, because a count without
    coverage context is misleading — zero events may mean zero exceptions
    or zero watching (ARCHITECTURE.md 6.5).

BR-R-03 additionally makes the accept/correct/reject counts visible: the
system's own error rate is never hidden. Counts only — the rejected events
themselves never appear.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from guardian_lens.core.errors import NotFoundError, ScopeError
from guardian_lens.core.principal import HumanPrincipal
from guardian_lens.repositories.config import ConfigRepository
from guardian_lens.repositories.events import EventRepository
from guardian_lens.repositories.identity import IdentityRepository
from guardian_lens.tenancy.context import TenantContext

__all__ = ["ReportingService", "SummaryReport"]

GROUP_BY_CHOICES = frozenset({"zone", "rule", "day"})


@dataclass(frozen=True)
class SummaryReport:
    payload: dict[str, Any]


class ReportingService:
    def __init__(self, context: TenantContext) -> None:
        self._session = context.session
        self._events = EventRepository(context.session)
        self._config = ConfigRepository(context.session)
        self._identity = IdentityRepository(context.session)

    def summary(
        self,
        *,
        principal: HumanPrincipal,
        site_id: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        group_by: str,
    ) -> SummaryReport:
        # Scope: any role grants report read at its own sites; the check is
        # against the token's grants, mirroring the queue scope rule.
        if site_id not in principal.site_ids():
            raise ScopeError("site is outside your scope")
        site = self._config.get_site(site_id)
        if site is None:
            raise NotFoundError("site not found")

        rows = self._events.verified_counts(
            site_id=site_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            group_by=group_by,
            site_timezone=site.timezone,
        )
        user = self._identity.user_by_id(principal.user_id)
        payload = {
            "period": {
                "from": occurred_from.isoformat(),
                "to": occurred_to.isoformat(),
            },
            "generated_by": {
                "id": str(principal.user_id),
                "full_name": user.full_name if user else "",
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "basis": "verified_events_only",
            "group_by": group_by,
            "groups": [
                {group_by: str(row.group_label), "verified_count": int(row.verified_count)}
                for row in rows
            ],
            # BR-R-03 — acceptance and rejection counts, visible.
            "decision_counts": self._events.decision_counts(
                site_id=site_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            ),
            "coverage_gaps_minutes": self._config.gap_minutes_overlapping(
                site_id=site_id,
                window_from=occurred_from,
                window_to=occurred_to,
            ),
        }
        return SummaryReport(payload)

    def export_csv(
        self,
        *,
        principal: HumanPrincipal,
        site_id: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        group_by: str,
    ) -> str:
        """CSV with a provenance header: period, generating user, basis —
        BR-R-02. The header travels INSIDE the file, because a file is
        forwarded without its HTTP response."""
        report = self.summary(
            principal=principal,
            site_id=site_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            group_by=group_by,
        ).payload

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["# Guardian Lens verified-events report"])
        writer.writerow(["# period_from", report["period"]["from"]])
        writer.writerow(["# period_to", report["period"]["to"]])
        writer.writerow(["# generated_by", report["generated_by"]["full_name"]])
        writer.writerow(["# generated_at", report["generated_at"]])
        writer.writerow(["# basis", report["basis"]])
        writer.writerow(
            ["# coverage_gaps_minutes", report["coverage_gaps_minutes"]]
        )
        counts = report["decision_counts"]
        writer.writerow(
            ["# decisions_accepted_corrected_rejected",
             counts["accepted"], counts["corrected"], counts["rejected"]]
        )
        writer.writerow([group_by, "verified_count"])
        for group in report["groups"]:
            writer.writerow([group[group_by], group["verified_count"]])
        return buffer.getvalue()
