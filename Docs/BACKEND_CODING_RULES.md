# Guardian Lens --- Backend Coding Rules

**Document:** Backend Coding Rules\
**Status:** Mandatory for development\
**Authority:** `TRD.md` + these coding rules\
**Scope:** Python/FastAPI backend, domain logic, database access,
tenancy, integrations, workers, tests, and backend tooling

------------------------------------------------------------------------

# 1. Purpose

This document defines the mandatory coding rules for the Guardian Lens
backend.

The TRD is the source of truth for:

-   Product and business requirements
-   Architecture
-   Technology decisions
-   Module responsibilities
-   API contracts
-   Database design
-   Security requirements
-   AI/ML boundaries
-   MVP/V1/V2 scope
-   Operational and deployment requirements

This document defines **how the backend code must be written**.

These rules apply equally to:

-   Human developers
-   AI coding assistants
-   Generated code
-   Refactors
-   Bug fixes
-   New features
-   Database changes
-   Background workers
-   Tests

If this document and the TRD conflict, the conflict must be reported
before implementation. Do not silently choose an interpretation.

If the TRD marks a requirement as `[OPEN]`, do not resolve it by
assumption.

------------------------------------------------------------------------

# 2. Mandatory Language

The following terms are normative:

-   **MUST** --- mandatory.
-   **MUST NOT** --- prohibited.
-   **SHOULD** --- recommended unless there is a documented reason not
    to.
-   **SHOULD NOT** --- normally prohibited unless justified.
-   **MAY** --- optional.

When a rule is marked **ABSOLUTE**, it must not be bypassed for
convenience, testing, demos, or temporary implementation.

------------------------------------------------------------------------

# 3. Core Principles

The backend MUST follow these principles:

1.  Correctness over convenience.
2.  Explicit behaviour over hidden behaviour.
3.  Small, focused modules over large general-purpose modules.
4.  Business rules must be explicit and testable.
5.  Security boundaries must be enforced server-side.
6.  Database integrity is part of application correctness.
7.  Tenant isolation is a security boundary.
8.  Auditability must not be bypassed.
9.  Do not invent requirements.
10. Do not introduce architecture that is not defined or approved.
11. Do not add functionality outside the requested scope.
12. Do not weaken tests or constraints to make code pass.
13. Prefer simple implementations over premature abstraction.
14. Avoid duplication, but do not create abstractions without a real
    reuse case.
15. Every production behaviour must be observable through appropriate
    logs, metrics, or audit records as required by the TRD.

------------------------------------------------------------------------

# 4. TRD Compliance

Before implementing a feature, the developer or AI tool MUST:

1.  Read the relevant section of `TRD.md`.
2.  Identify the applicable business rules.
3.  Identify the applicable security requirements.
4.  Identify the applicable database requirements.
5.  Identify whether the feature is `[MVP]`, `[V1]`, or `[V2+]`.
6.  Check for `[OPEN]` requirements.
7.  Check whether the requested behaviour conflicts with an existing
    architecture decision.

Do not:

-   Invent missing fields.
-   Invent missing API behaviour.
-   Invent fallback behaviour.
-   Invent permissions.
-   Invent tenant behaviour.
-   Invent business rules.
-   Implement `[V1]` or `[V2+]` functionality in MVP unless explicitly
    requested and approved.

------------------------------------------------------------------------

# 5. Backend Architecture

The backend MUST preserve the architectural dependency direction:

``` text
API / Controller
       ↓
Application Service
       ↓
Domain Rules / Guards
       ↓
Repository
       ↓
Database
```

Infrastructure integrations are accessed through defined
interfaces/adapters.

## 5.1 Controllers

Controllers MUST:

-   Handle HTTP concerns only.
-   Validate input through request schemas.
-   Obtain authenticated identity from the security context.
-   Obtain tenant context from the tenancy context.
-   Call application services.
-   Return response schemas.
-   Translate expected domain errors into appropriate API responses.

Controllers MUST NOT:

-   Contain business logic.
-   Contain SQL.
-   Create database engines.
-   Select tenant databases.
-   Perform authorization decisions that belong to the authorization
    layer.
-   Mutate ORM entities directly.
-   Implement complex transactions.
-   Call external services directly unless explicitly defined as an
    integration boundary.

## 5.2 Services

Services MUST:

-   Orchestrate application behaviour.
-   Coordinate repositories, guards, and integrations.
-   Define transaction boundaries where required.
-   Enforce workflow sequencing.
-   Operate inside the already-resolved tenant context.

Services MUST NOT:

-   Manually select tenant databases.
-   Create database engines.
-   Contain raw SQL.
-   Implement HTTP-specific behaviour.
-   Duplicate repository functionality.

## 5.3 Domain Rules and Guards

Business rules MUST be implemented as explicit, reusable, testable
units.

Rules that protect core product commitments MUST be represented by
guards or equivalent domain enforcement mechanisms.

Do not duplicate the same rule across controllers, services,
repositories, and workers.

A guard MUST fail explicitly when its condition is not satisfied.

## 5.4 Repositories

Repositories MUST:

-   Handle database persistence and retrieval.
-   Use the database session supplied by the application/infrastructure
    layer.
-   Keep queries focused on their aggregate/entity responsibility.
-   Apply required data visibility rules.

Repositories MUST NOT:

-   Resolve tenant identity from client input.
-   Create tenant database connections.
-   Make unrelated business decisions.
-   Contain HTTP logic.
-   Perform workflow orchestration.

------------------------------------------------------------------------

# 6. Tenant Isolation --- ABSOLUTE

Guardian Lens uses **database-per-tenant isolation**.

Tenant isolation is a security boundary, not merely a filtering
convention.

The application MUST resolve the tenant before accessing tenant-owned
data.

The intended flow is:

``` text
Request
  ↓
Authentication
  ↓
Tenant Resolution
  ↓
Tenant Context
  ↓
Tenant Database Session
  ↓
Service
  ↓
Repository
  ↓
Tenant Database
```

## 6.1 Tenant Context

Tenant context MUST be explicit and available to all tenant-scoped
operations.

A tenant context SHOULD contain, as required by the architecture:

-   `tenant_id`
-   Authenticated `user_id`
-   Roles/permissions
-   Trusted database reference/key
-   Tenant state

The exact structure MUST follow the tenancy architecture defined in
`TRD.md`.

## 6.2 Tenant Identity

Tenant identity MUST come from a trusted authenticated/system context.

Tenant identity MUST NOT be trusted from:

-   Request body
-   Query parameters
-   Arbitrary URL parameters
-   Frontend state
-   Hidden form fields
-   Client-controlled headers
-   Untrusted job payloads

If a request contains a tenant identifier, it MUST be validated against
the authenticated tenant context. It MUST NOT override it.

## 6.3 Tenant Database Selection

Tenant database selection MUST be centralized in the tenancy
infrastructure.

Only the tenancy infrastructure may:

-   Resolve tenant → database
-   Obtain tenant database credentials
-   Create/reuse tenant database engines
-   Create tenant sessions
-   Manage tenant connection pools

Controllers, services, repositories, domain code, and frontend code MUST
NOT construct tenant database connections.

Forbidden:

``` python
engine = create_async_engine(tenant.database_url)
```

inside business/application code.

## 6.4 One Request, One Tenant

A normal tenant-scoped API request MUST operate against exactly one
tenant database.

Cross-tenant queries are prohibited unless explicitly designed,
authorized, audited, and approved as a separate system capability.

Do not implement cross-tenant access by looping through tenant
databases.

## 6.5 No Shared-Database Fallback

Tenant data MUST NOT silently fall back to:

-   A shared database
-   A default tenant
-   A system database
-   A development database
-   An unscoped connection

A missing or invalid tenant context MUST fail closed.

## 6.6 Background Jobs

Every tenant-scoped background job MUST carry sufficient trusted tenant
context to resolve the correct tenant database.

Worker execution MUST follow:

``` text
Job
 ↓
Resolve tenant
 ↓
Validate tenant state
 ↓
Open tenant session
 ↓
Execute operation
 ↓
Commit / rollback
 ↓
Close session
```

Workers MUST NOT use a default tenant database for tenant-scoped work.

## 6.7 Tenant Database Sessions

Tenant sessions MUST be created through the centralized tenancy/session
infrastructure.

Do not create a new database engine or connection pool per request.

Tenant engine and pool lifecycle MUST be centrally managed.

## 6.8 Tenant Schema Version

All active tenant databases MUST use a supported schema version.

Application code MUST NOT assume that one tenant migration succeeded for
all tenants.

Migration orchestration MUST track tenant schema status according to the
architecture defined in `TRD.md`.

## 6.9 Tenant Provisioning

A tenant MUST NOT become active until:

1.  Tenant database is created.
2.  Required schema is applied.
3.  Required seed/configuration data is created.
4.  Schema version is validated.
5.  Provisioning succeeds.

Partial provisioning MUST fail safely.

## 6.10 Tenant Isolation Testing

The test suite MUST actively attempt tenant-isolation violations.

At minimum:

-   Tenant A cannot read Tenant B data.
-   Tenant A cannot modify Tenant B data.
-   Tenant A cannot access Tenant B evidence.
-   Tenant A cannot force Tenant B through request parameters.
-   Tenant A background jobs cannot execute against Tenant B.
-   Invalid tenant context fails closed.
-   Tenant database resolution cannot be overridden by client input.

Tenant-isolation failures MUST block CI.

------------------------------------------------------------------------

# 7. Naming Conventions

Use clear, descriptive names.

## Python

-   Modules/files: `snake_case.py`
-   Functions: `snake_case`
-   Variables: `snake_case`
-   Constants: `UPPER_SNAKE_CASE`
-   Classes: `PascalCase`
-   Exceptions: `PascalCase` ending in `Error`
-   Type aliases: `PascalCase`
-   Boolean variables: use meaningful prefixes such as `is_`, `has_`,
    `can_`, `should_`

Examples:

``` python
DecisionService
VerificationGuard
tenant_context
event_id
MAX_RETRY_COUNT
is_verified
```

Avoid:

``` python
d
tmp
data2
obj
stuff
helper
misc
```

unless the name is genuinely appropriate to the local context.

------------------------------------------------------------------------

# 8. File and Folder Structure

Organize code by responsibility and domain.

Recommended backend structure:

``` text
app/
├── api/
│   ├── dependencies/
│   └── routes/
├── domain/
│   ├── entities/
│   ├── rules/
│   ├── guards/
│   └── exceptions/
├── services/
├── repositories/
├── tenancy/
├── models/
├── schemas/
├── integrations/
├── workers/
└── core/
```

Do not create generic dumping-ground files such as:

``` text
utils.py
helpers.py
common.py
misc.py
```

unless their responsibility is narrow and clearly defined.

Avoid files containing unrelated functionality.

------------------------------------------------------------------------

# 9. Function and Class Design

Functions SHOULD have one clear responsibility.

Avoid:

-   Large functions
-   Deep nesting
-   Excessive branching
-   Multiple unrelated side effects
-   Hidden database operations
-   Hidden network calls

Extract logic when doing so makes the behaviour easier to understand or
test.

Do not split every three lines into a function merely to satisfy an
arbitrary line-count rule.

Classes MUST have a clear responsibility.

Avoid "god classes" that:

-   Validate input
-   Query the database
-   Send HTTP requests
-   Apply business rules
-   Write audit records
-   Format API responses

all in one class.

------------------------------------------------------------------------

# 10. Type Safety

Python application code MUST use type hints.

Prefer:

``` python
async def get_event(
    event_id: UUID,
    tenant: TenantContext,
) -> EventResponse:
    ...
```

Avoid untyped public functions.

`Any` SHOULD NOT be used unless necessary and documented.

Avoid dynamic dictionaries when a Pydantic model, dataclass, enum, or
typed object provides clearer structure.

------------------------------------------------------------------------

# 11. Pydantic and API Schemas

Use Pydantic models for external API input/output.

Do not expose ORM/database models directly as API responses.

Separate:

``` text
Request Schema
Response Schema
Persistence Model
Domain Model
```

when their responsibilities differ.

Never allow clients to submit server-owned fields such as:

-   `reviewer_id`
-   `tenant_id`
-   audit metadata
-   server timestamps
-   internal status fields

unless explicitly defined by the API contract.

------------------------------------------------------------------------

# 12. API Rules

Follow API contracts defined by the TRD.

Use:

``` text
/api/v1/...
```

for versioned APIs where defined.

Use appropriate HTTP methods and status codes.

API handlers MUST:

1.  Authenticate.
2.  Resolve tenant context.
3.  Authorize the operation.
4.  Validate input.
5.  Call the service.
6.  Return the defined response.

Do not expose internal exception details, SQL errors, stack traces,
credentials, or database information to API consumers.

API behaviour must remain idempotent where the TRD requires idempotency.

------------------------------------------------------------------------

# 13. Authentication and Authorization

Authentication MUST be enforced server-side.

Authorization MUST be enforced server-side.

Never trust the frontend to enforce permissions.

The authenticated principal is authoritative for user identity.

Do not accept user identity from request data when the identity is
available from the authentication context.

Follow RBAC and scope rules defined by the TRD.

Default to deny when authorization cannot be established.

Agents MUST NOT receive reviewer capabilities.

Authorization checks MUST happen before sensitive data access or
mutation.

------------------------------------------------------------------------

# 14. Database Coding Rules

PostgreSQL is the system of record for the control plane as defined by
the TRD.

Use SQLAlchemy for application database access unless the TRD explicitly
requires another mechanism.

Use Alembic for schema migrations.

Every schema change MUST have a migration.

Never manually modify production schema.

## 14.1 Query Rules

-   Prefer SQLAlchemy expressions.
-   Never construct SQL using untrusted string interpolation.
-   Use parameterized queries.
-   Avoid N+1 queries.
-   Avoid unnecessary database round trips.
-   Select only required fields when appropriate.
-   Use pagination for potentially large result sets.
-   Use indexes defined by the data-access pattern.
-   Do not bypass database constraints.

## 14.2 Integrity

Application logic MUST NOT be used as a substitute for database
constraints when the TRD requires data-layer enforcement.

Do not remove:

-   CHECK constraints
-   Foreign keys
-   Unique constraints
-   Triggers
-   Required indexes

to make implementation easier.

## 14.3 Transactions

Transactions MUST be explicit around operations requiring atomicity.

Where the TRD requires:

``` text
Business mutation + Audit record
```

both MUST occur in the same database transaction.

If the audit write fails, the business mutation MUST roll back.

------------------------------------------------------------------------

# 15. Audit Rules

Audit records are different from application logs.

Required mutations MUST create audit records according to the TRD.

Audit records MUST be append-only.

Application code MUST NOT:

-   Update audit records.
-   Delete audit records.
-   Silently replace audit records.
-   Use application logs as a substitute for required audit records.

Audit and the associated tenant mutation MUST use the same tenant
database transaction where required.

------------------------------------------------------------------------

# 16. Error and Exception Handling

Use explicit domain/application exceptions.

Examples:

``` text
EventNotFoundError
InvalidDecisionError
UnauthorizedDecisionError
TenantNotFoundError
TenantAccessDeniedError
TenantDatabaseUnavailableError
ConcurrentDecisionError
```

Do not use generic exceptions for expected business conditions.

Do not silently swallow exceptions.

Forbidden:

``` python
try:
    ...
except Exception:
    pass
```

Do not catch an exception unless the code can:

-   Recover
-   Translate it
-   Add meaningful context
-   Log it appropriately
-   Re-raise it

Unexpected exceptions must remain observable.

------------------------------------------------------------------------

# 17. Logging

Use structured logging as defined by the TRD.

Logs SHOULD include appropriate context such as:

-   `timestamp`
-   `level`
-   `channel`
-   `service`
-   `trace_id`
-   `tenant_id`
-   `user_id`
-   `event`
-   relevant entity reference
-   duration where useful

Never log:

-   Passwords
-   JWT contents
-   Refresh tokens
-   Database passwords
-   Connection strings containing credentials
-   Camera credentials
-   Stream credentials
-   Evidence binary data
-   Prohibited per-person activity metrics

Audit records MUST NOT be replaced by normal application logging.

------------------------------------------------------------------------

# 18. External Integrations

External systems MUST be accessed through dedicated integration
modules/interfaces.

Do not scatter HTTP client calls throughout services.

Integration code MUST handle:

-   Timeouts
-   Expected failures
-   Retries where appropriate
-   Authentication
-   Response validation
-   Logging
-   Error translation

Do not introduce an external integration that is prohibited or not
approved by the TRD.

------------------------------------------------------------------------

# 19. AI / ML Boundaries

The backend MUST preserve the AI/ML boundaries defined by the TRD.

AI MUST NOT:

-   Auto-approve events.
-   Auto-reject verified records.
-   Identify individuals.
-   Perform facial recognition.
-   Perform person re-identification.
-   Calculate individual productivity/activity metrics.
-   Trigger HR or disciplinary actions.
-   Introduce prohibited inference capabilities.

AI output MUST NOT bypass human verification where human verification is
required.

Model versions and relevant inference metadata MUST remain traceable
where required.

------------------------------------------------------------------------

# 20. Evidence and Object Storage

Evidence access MUST be tenant-scoped and authorization-checked.

The application MUST NOT assume that possession of an object identifier
grants access.

Before returning evidence:

``` text
Authenticated User
        ↓
Tenant Context
        ↓
Object Ownership / Tenant Check
        ↓
Authorization
        ↓
Evidence Access
```

Raw video MUST NOT be centrally stored where prohibited by the TRD.

Evidence storage MUST remain behind the defined storage abstraction.

------------------------------------------------------------------------

# 21. Background Workers

Workers MUST be deterministic, observable, and tenant-aware where
applicable.

Workers MUST:

-   Validate input.
-   Resolve tenant context.
-   Use appropriate transactions.
-   Handle failures explicitly.
-   Release database resources.
-   Avoid duplicate processing where idempotency is required.
-   Produce appropriate logs/metrics.

Workers MUST NOT bypass authentication/authorization rules simply
because they run internally.

System-level worker operations must use explicitly authorized system
context.

------------------------------------------------------------------------

# 22. Configuration

Configuration MUST come from the configured application
settings/environment mechanism.

Do not hardcode:

-   Secrets
-   Credentials
-   Database URLs
-   API keys
-   Environment-specific URLs
-   Tenant credentials
-   Security keys

Use typed configuration where possible.

Configuration changes MUST NOT silently change business rules unless
explicitly designed and audited according to the TRD.

------------------------------------------------------------------------

# 23. Dependencies

Do not add a dependency without a real requirement.

Before adding a package:

1.  Check whether the existing stack already provides the capability.
2.  Check whether the package is compatible with the supported Python
    version.
3.  Check security/licensing implications.
4.  Check maintenance status.
5.  Check whether it violates the TRD.
6.  Prefer established dependencies already used by the project.

Never add a prohibited dependency.

In particular, dependencies for facial recognition or person
re-identification are prohibited.

------------------------------------------------------------------------

# 24. Comments and Documentation

Comments should explain **why**, not restate obvious code.

Bad:

``` python
# Check if status is unverified
if event.status == EventStatus.UNVERIFIED:
```

Good:

``` python
# Only unverified events may enter human verification.
# This protects the single-step decision workflow.
VerificationGuard.ensure_unverified(event)
```

Document:

-   Non-obvious business decisions.
-   Security-sensitive behaviour.
-   Complex algorithms.
-   External integration assumptions.
-   Workarounds that are explicitly approved.
-   Important architectural constraints.

Do not use comments to justify prohibited behaviour.

Do not leave misleading comments after refactoring.

------------------------------------------------------------------------

# 25. Constants and Enums

Do not scatter magic numbers or strings through application code.

Bad:

``` python
if event.status == "unverified":
```

when a defined enum exists.

Prefer:

``` python
if event.status == EventStatus.UNVERIFIED:
```

Use constants for stable configuration values where appropriate.

Do not create constants for values that are meaningful only once.

------------------------------------------------------------------------

# 26. Concurrency and Idempotency

Operations defined as idempotent by the TRD MUST remain idempotent.

Do not rely only on application checks for uniqueness when the database
can enforce it.

For concurrent updates:

-   Use transactions.
-   Use optimistic locking/version checks where defined.
-   Handle conflicts explicitly.
-   Do not silently overwrite another user's change.

The implementation MUST preserve the TRD behaviour for stale versions
and concurrent decisions.

------------------------------------------------------------------------

# 27. Database Migrations

Every schema change MUST be represented by a migration.

Migrations MUST:

-   Be reviewed.
-   Be deterministic.
-   Be safe to run in the intended environment.
-   Follow the expand-contract strategy where required.
-   Preserve audit data.
-   Preserve backward compatibility according to deployment
    requirements.
-   Support the tenant migration strategy.

Never:

-   Drop audit data to solve a migration problem.
-   Modify production schema manually.
-   Mark a migration complete when tenant databases have not been
    migrated.
-   Make application code depend on a schema change that has not been
    deployed safely.

------------------------------------------------------------------------

# 28. Testing Rules

Every new behaviour MUST have appropriate tests.

Required levels where applicable:

``` text
Unit
Integration
Business-rule bypass
End-to-end
```

Tests MUST be:

-   Deterministic.
-   Isolated.
-   Repeatable.
-   Meaningfully named.
-   Independent of execution order.

Test names should describe behaviour:

``` python
def test_decision_requires_unverified_event():
    ...

def test_reviewer_identity_comes_from_authenticated_principal():
    ...

def test_tenant_a_cannot_access_tenant_b_event():
    ...
```

Do not:

-   Delete tests to make CI pass.
-   Disable tests temporarily.
-   Skip security tests without an approved reason.
-   Use production data in tests.
-   Depend on another test's execution order.

Business-rule guards require complete pass/fail coverage according to
the TRD.

Tenant-isolation tests are mandatory and blocking.

------------------------------------------------------------------------

# 29. Test Database Rules

Integration tests MUST use isolated test databases.

Never run tests against production databases.

Tenant-isolation integration tests SHOULD create at least two tenant
contexts/databases:

``` text
Tenant A
Tenant B
```

and explicitly attempt cross-tenant access.

Test cleanup MUST not depend on production retention mechanisms.

------------------------------------------------------------------------

# 30. Code Quality

Backend code MUST pass the project quality gates defined by the TRD.

At minimum, where configured:

``` text
ruff
mypy
pytest
security scans
integration tests
business-rule bypass suite
```

Do not suppress lint/type/security findings without justification.

Do not add broad exclusions simply to make CI pass.

Prefer fixing the code over suppressing the check.

------------------------------------------------------------------------

# 31. Refactoring Rules

Refactoring MUST preserve behaviour unless the change explicitly
includes a behaviour change.

Do not combine unrelated refactoring with a feature unless necessary.

When refactoring:

1.  Understand existing tests.
2.  Preserve business rules.
3.  Preserve authorization.
4.  Preserve tenant isolation.
5.  Preserve audit behaviour.
6.  Preserve API contracts unless intentionally changed.
7.  Run relevant tests.

Do not refactor by removing constraints or bypassing guards.

------------------------------------------------------------------------

# 32. Technical Debt

Technical debt MUST be explicit.

Do not leave:

``` text
TODO: fix later
```

for security, authorization, tenant isolation, auditability, or core
business rules.

The following are NOT acceptable technical debt:

-   Missing tenant isolation.
-   Application-only enforcement where database enforcement is required.
-   Disabled security checks.
-   Disabled business-rule tests.
-   Temporary auto-approval paths.
-   Shared-database fallback for tenant data.
-   Hardcoded secrets.
-   Central raw-video storage where prohibited.
-   Bypassed audit logging.

------------------------------------------------------------------------

# 33. Forbidden Patterns

The following patterns are prohibited:

-   Business logic inside controllers.
-   SQL inside controllers.
-   Manual tenant database selection in services.
-   Manual tenant database selection in repositories.
-   Per-request creation of tenant connection pools.
-   Shared database fallback for tenant data.
-   Trusting client-supplied tenant identity.
-   Cross-tenant access from normal tenant APIs.
-   Direct ORM/database access from controllers.
-   `except Exception: pass`.
-   Hardcoded credentials.
-   Hardcoded secrets.
-   Logging secrets.
-   Dynamic SQL using untrusted input.
-   Removing database constraints to fix application errors.
-   Commenting out failing tests.
-   Deleting tests to make CI green.
-   Temporary authentication bypasses.
-   Temporary authorization bypasses.
-   Temporary auto-approval paths.
-   Facial recognition dependencies.
-   Person re-identification dependencies.
-   Individual productivity/activity calculations.
-   Central raw-video storage where prohibited.
-   Unapproved external integrations.
-   Unapproved architecture changes.

------------------------------------------------------------------------

# 34. AI Coding Tool Rules

AI coding tools MUST treat this document as mandatory instructions.

Before modifying code, an AI tool MUST:

1.  Read `CODING_RULES.md`.
2.  Read the relevant `TRD.md` section.
3.  Inspect the existing implementation.
4.  Identify affected modules.
5.  Identify affected business rules.
6.  Identify affected tenant boundaries.
7.  Identify required tests.

AI tools MUST NOT:

-   Invent requirements.
-   Invent APIs.
-   Invent database fields.
-   Invent permissions.
-   Invent tenant behaviour.
-   Change architecture without approval.
-   Introduce a shared database fallback.
-   Bypass tenant isolation.
-   Accept client-supplied tenant identity as authoritative.
-   Create tenant database connections inside business code.
-   Remove constraints.
-   Remove tests.
-   Disable security checks.
-   Add prohibited capabilities.
-   Modify unrelated files without reason.

If the requested implementation conflicts with `TRD.md`, the AI tool
MUST stop and report the conflict.

If the required behaviour is marked `[OPEN]`, the AI tool MUST stop and
request clarification.

After implementation, the AI tool MUST:

1.  Run relevant tests.
2.  Run lint/type checks.
3.  Run security checks where applicable.
4.  Report files changed.
5.  Report tests/checks executed.
6.  Report any unresolved issue.

------------------------------------------------------------------------

# 35. Definition of Done

A backend change is complete only when:

-   The requested requirement is implemented.
-   The relevant TRD requirements are followed.
-   Architecture boundaries are preserved.
-   Tenant isolation is preserved.
-   Authentication and authorization are enforced.
-   Business rules are enforced.
-   Database constraints remain intact.
-   Audit requirements are satisfied.
-   Appropriate tests exist.
-   Tenant-isolation tests pass where applicable.
-   Lint passes.
-   Type checks pass.
-   Security checks pass.
-   Database migrations are included where required.
-   API contracts are updated where required.
-   No prohibited functionality was introduced.
-   No unresolved `[OPEN]` requirement was guessed.
-   No unrelated behaviour was changed.

------------------------------------------------------------------------

# 36. Final Development Rule

When there is uncertainty:

``` text
1. Check CODING_RULES.md
2. Check the relevant TRD section
3. Check the relevant PRD requirement
4. Check existing tests
5. Do not guess
6. Ask for clarification if the requirement is unresolved
```

The objective is not to produce the fastest code.

The objective is to produce code that remains:

-   Correct
-   Secure
-   Tenant-isolated
-   Auditable
-   Testable
-   Maintainable
-   Consistent with the TRD
-   Safe for human developers and AI coding tools
