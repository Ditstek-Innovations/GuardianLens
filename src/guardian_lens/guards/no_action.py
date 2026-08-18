"""NoActionGuard — BR-003: no outbound consequence integration exists.

The integration layer's HR / performance / disciplinary row reads "NONE —
must not exist" (TRD 6.5). That is a negative property, so the guard is a
dependency-graph inspection rather than a runtime check: it walks the
imported guardian_lens modules and the installed dependency set and fails
if anything consequence-shaped appears. The bypass suite runs it on every
CI execution (TRD 6.3: "static analysis: assert no HR/performance client
exists in the dependency graph").

This does not prove a negative forever; it makes adding the integration a
reviewable event — the same posture as the negative schema
(DATABASE.md 4).
"""

from __future__ import annotations

import sys

#: Substrings that indicate a consequence integration or a prohibited
#: capability, checked against module names in the dependency graph.
FORBIDDEN_MODULE_MARKERS: tuple[str, ...] = (
    "hr_",
    "_hr",
    "webhook",
    "disciplinary",
    "performance_review",
    "escalation",
    # Prohibited inference capabilities (BACKEND_CODING_RULES 23).
    "face_recognition",
    "facial_recognition",
    "reidentification",
    "person_reid",
    "deepface",
)


class NoActionGuard:
    @staticmethod
    def assert_no_consequence_integrations() -> None:
        """Fail if any guardian_lens module, or any module it caused to be
        imported, matches a forbidden marker."""
        offenders = [
            name
            for name in sys.modules
            if name.startswith("guardian_lens")
            and any(marker in name.lower() for marker in FORBIDDEN_MODULE_MARKERS)
        ]
        if offenders:
            raise AssertionError(
                f"consequence/prohibited integration present in dependency "
                f"graph (BR-003): {sorted(offenders)}"
            )

    @staticmethod
    def scan_module_names(names: list[str]) -> list[str]:
        """Pure helper for the CI fitness function: return the offending
        subset of ``names``. Separated from the assertion so the test can
        exercise both the pass and the fail path (TRD 19.2)."""
        return sorted(
            name
            for name in names
            if any(marker in name.lower() for marker in FORBIDDEN_MODULE_MARKERS)
        )
