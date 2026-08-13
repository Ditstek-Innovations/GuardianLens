"""Application services — orchestration and transaction boundaries.

Services coordinate repositories, guards and integrations inside an
already-resolved tenant context (BACKEND_CODING_RULES 5.2). Transaction
boundaries per TRD 6.2: one transaction per ingest; ONE transaction
covering a decision and its audit entry; one covering a configuration
change and its audit entry. No service selects a tenant database, ever.
"""
