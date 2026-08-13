"""Versioned route modules mounted under /api/v1.

What is absent here is as deliberate as what is present (TRD 10.9): there
is no bulk decision route, no route setting status directly, no DELETE or
PATCH on /audit, no webhook or HR export route, and no route returning a
per-person aggregate. Their absence is the architecture.
"""
