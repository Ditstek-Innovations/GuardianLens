"""Core: typed settings, domain errors, structured logging, principals.

Nothing in this package touches a database or an HTTP request. It exists so
that every other layer shares one vocabulary for configuration, failure and
identity — BACKEND_CODING_RULES 8 calls this ``core/``.
"""
