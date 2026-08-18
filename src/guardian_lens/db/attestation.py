"""FF-11 — per-tenant constraint attestation.

Under ADR-016 there is one database per tenant, so every constraint and
trigger that makes BR-004 and BR-005 structural exists **N times**. The
product's central guarantee is therefore only as strong as the weakest
tenant's schema, and a tenant provisioned by hand or left half-migrated
after a failed fan-out is a database in which a verified record with no
reviewer is insertable — invisibly, unless something looks.

This is what looks. It runs in CI **and continuously in production**
(ARCHITECTURE.md 8.2.3, threat T-18, risk R-9).

Two properties worth stating:

  * Attestation is INDEPENDENT of migration success. A migration that
    returns zero and a database that lacks a trigger are different facts,
    and only the second one matters. This asserts the presence of objects,
    never the outcome of a command.

  * A tenant failing attestation is SUSPENDED from binding, not merely
    alerted. Serving a database whose rule enforcement is unverified is
    worse than serving an error. The temptation to resist is letting a
    drifted tenant keep serving because "it is only one migration behind" —
    whether that is safe depends entirely on which migration it is, and the
    team making that judgement under pressure is the erosion GOVERNANCE.md
    section 8 exists to prevent.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import psycopg

from guardian_lens.db.urls import psycopg_url
from guardian_lens.rules.registry import ENFORCEMENT, Enforcement, ObjectKind

__all__ = ["Finding", "AttestationResult", "attest", "attest_url", "main"]


@dataclass(frozen=True, slots=True)
class Finding:
    enforcement: Enforcement
    present: bool
    enabled: bool
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.present and self.enabled


@dataclass(slots=True)
class AttestationResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if not f.ok]

    @property
    def blocking_failures(self) -> list[Finding]:
        """Failures on ACTIVE rules. These suspend the tenant."""
        return [f for f in self.failures if f.enforcement.is_release_blocking]

    @property
    def advisory_failures(self) -> list[Finding]:
        """Failures on PROPOSED rules and coherence invariants.

        Reported, not gating: a PROPOSED rule carries no force until
        ratified (RULE_BOOK.md section 8, item 6) and must not be cited to
        block work.
        """
        return [f for f in self.failures if not f.enforcement.is_release_blocking]

    @property
    def ok(self) -> bool:
        """True when nothing release-blocking is missing."""
        return not self.blocking_failures

    def report(self) -> str:
        lines = [
            f"FF-11 attestation: {len(self.findings)} objects checked, "
            f"{len(self.failures)} failing "
            f"({len(self.blocking_failures)} blocking)",
        ]
        for f in self.failures:
            tag = "BLOCKING" if f.enforcement.is_release_blocking else "advisory"
            rules = ", ".join(f.enforcement.rules) or "-"
            lines.append(
                f"  [{tag}] {f.enforcement.kind.value} "
                f"{f.enforcement.table}.{f.enforcement.name} "
                f"(rules: {rules}) — {f.detail}"
            )
        if self.ok and not self.failures:
            lines.append("  all present and enabled")
        return "\n".join(lines)


_CONSTRAINT_SQL = """
    SELECT c.contype, c.convalidated
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
     WHERE n.nspname = current_schema()
       AND t.relname = %s
       AND c.conname = %s
"""

# tgenabled: 'O' origin (normal), 'D' disabled, 'R' replica, 'A' always.
# A DISABLEd trigger is present and useless, which is precisely the state an
# attacker or a careless migration would leave behind.
_TRIGGER_SQL = """
    SELECT tg.tgenabled
      FROM pg_trigger tg
      JOIN pg_class t ON t.oid = tg.tgrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
     WHERE n.nspname = current_schema()
       AND NOT tg.tgisinternal
       AND t.relname = %s
       AND tg.tgname = %s
"""

_INDEX_SQL = """
    SELECT 1
      FROM pg_indexes
     WHERE schemaname = current_schema()
       AND tablename = %s
       AND indexname = %s
"""


def _check(conn: psycopg.Connection, e: Enforcement) -> Finding:
    with conn.cursor() as cur:
        if e.kind in (ObjectKind.CHECK, ObjectKind.UNIQUE):
            cur.execute(_CONSTRAINT_SQL, (e.table, e.name))
            row = cur.fetchone()
            if row is None:
                return Finding(e, present=False, enabled=False, detail="not found")
            contype, validated = row
            expected = "c" if e.kind is ObjectKind.CHECK else "u"
            if contype != expected:
                return Finding(
                    e,
                    present=True,
                    enabled=False,
                    detail=f"wrong constraint type {contype!r}, expected {expected!r}",
                )
            if not validated:
                # ADD CONSTRAINT ... NOT VALID without a later VALIDATE leaves
                # existing rows unchecked. Present but not yet a guarantee.
                return Finding(e, present=True, enabled=False, detail="NOT VALID")
            return Finding(e, present=True, enabled=True)

        if e.kind is ObjectKind.TRIGGER:
            cur.execute(_TRIGGER_SQL, (e.table, e.name))
            row = cur.fetchone()
            if row is None:
                return Finding(e, present=False, enabled=False, detail="not found")
            (tgenabled,) = row
            if tgenabled == "D":
                return Finding(e, present=True, enabled=False, detail="DISABLED")
            return Finding(e, present=True, enabled=True)

        cur.execute(_INDEX_SQL, (e.table, e.name))
        if cur.fetchone() is None:
            return Finding(e, present=False, enabled=False, detail="not found")
        return Finding(e, present=True, enabled=True)


def attest(conn: psycopg.Connection) -> AttestationResult:
    """Verify every registered enforcement object in one tenant database."""
    return AttestationResult([_check(conn, e) for e in ENFORCEMENT])


def attest_url(url: str) -> AttestationResult:
    with psycopg.connect(psycopg_url(url)) as conn:
        return attest(conn)


def main(argv: list[str] | None = None) -> int:
    import os

    argv = list(sys.argv[1:] if argv is None else argv)
    target = argv[0] if argv else os.environ.get("GL_TENANT_DB_URL", "")
    if not target:
        print(
            "usage: python -m guardian_lens.db.attestation <tenant-db-url|slug>\n"
            "   or: set GL_TENANT_DB_URL",
            file=sys.stderr,
        )
        return 2
    if "://" in target:
        url = target
    else:
        # A bare slug: derive the URL the way provisioning does, from the
        # base connection in GL_TENANT_DB_URL.
        from guardian_lens.db.urls import tenant_url

        base = os.environ.get("GL_TENANT_DB_URL", "")
        if not base:
            print("a slug needs GL_TENANT_DB_URL as the base", file=sys.stderr)
            return 2
        url = tenant_url(base, target)

    result = attest_url(url)
    print(result.report())
    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
