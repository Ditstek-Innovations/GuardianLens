"""Repositories — data access against an already-bound tenant session.

Repositories receive the session; they never resolve tenant identity or
create connections (BACKEND_CODING_RULES 5.4). Data-visibility rules that
protect product commitments are applied HERE, not left to callers:
site-scope filters on every scoped read (TRD 12.3 enforcement point 2) and
the verified-only filter on every reporting read (BR-R-01).
"""
