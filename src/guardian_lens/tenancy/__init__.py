"""Tenancy infrastructure — the ONLY code allowed to touch tenant routing.

BACKEND_CODING_RULES 6.3: only this package may resolve tenant → database,
create or reuse tenant engines, and create tenant sessions. Controllers,
services and repositories receive an already-bound session and cannot
construct one — there is no unbound query path.
"""

from guardian_lens.tenancy.context import TenantContext
from guardian_lens.tenancy.registry import TenantRecord, TenantRegistry
from guardian_lens.tenancy.router import TenantRouter

__all__ = ["TenantContext", "TenantRecord", "TenantRegistry", "TenantRouter"]
