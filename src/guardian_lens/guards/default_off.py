"""DefaultOffGuard — BR-001, BR-C-02: nothing is monitored by default.

A detection rule is created inactive and becomes active only through an
explicit activation carrying a named user and a timestamp. The database
enforces the same pair via detection_rules.is_active DEFAULT FALSE and
chk_active_rule_has_activator; this guard makes the service path refuse
earlier and with a domain error.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID


class DefaultOffGuard:
    @staticmethod
    def ensure_created_inactive(is_active: bool) -> None:
        """No creation path may produce an active rule. Activation is a
        separate, attributed act (TRD 11.5) — there is no path by which a
        rule becomes active without a named user having activated it."""
        if is_active:
            raise ValueError(
                "a detection rule cannot be created active (BR-001); "
                "activate it explicitly after creation"
            )

    @staticmethod
    def ensure_named_activator(
        activated_by: UUID | None, activated_at: datetime | None
    ) -> None:
        """Activation must carry who and when, from the authenticated
        principal — never defaulted, never inferred."""
        if activated_by is None or activated_at is None:
            raise ValueError(
                "rule activation requires a named activator and timestamp "
                "(BR-C-02)"
            )
