"""Control-plane API — controllers, dependencies, app factory.

Controllers handle HTTP concerns only: parse, authenticate via the
security dependencies, call a service, serialise (BACKEND_CODING_RULES
5.1). Business logic lives in services/, rules in guards/, persistence in
repositories/, and tenant binding in tenancy/ — a controller cannot reach
a database except through a bound TenantContext handed to it.
"""
