# Guardian Lens — Frontend Coding Standards

**The normative engineering standard for the React + TypeScript codebase: contract-driven, accessible, secure, testable and deliberately consistent.**

| Field | Value |
|---|---|
| Document | Coding Standards (Frontend — React + TypeScript) |
| Version | 1.3 |
| Status | Draft for review |
| Programme phase | Week 3 — Govern · 8 August 2026 |
| Applies to | `web/` — the Review Web App (TRD §7). Backend Python standards are a separate document. |
| Inputs | TRD v1.0 §3 (stack), §7 (frontend architecture), §10 (API), §17 (performance), §19 (testing), §21 (NFRs) · RULE_BOOK v1.0 §4 · PRD v1.0 §4 (design principles) |
| Authority | **This document is normative for *how* frontend code is written.** Where it conflicts with the TRD on *what* is built, the TRD prevails. Where it conflicts with the RULE_BOOK on *what the product may do*, the RULE_BOOK prevails — always. Where it conflicts with personal preference, this document prevails. |
| Enforcement | Mechanical wherever possible (§21). A rule that cannot be linted is stated explicitly as a review item. |

---

## 0. What this document is, and how an agent must use it

This document exists because the codebase will be written largely by AI agents working from the PRD, TRD and Rule Book. An agent without a written standard produces code that is individually reasonable and collectively incoherent: five different buttons, three ways to fetch, types invented at the point of use and never reused.

**This document is the contract.** It is written to be executed, not admired.

### 0.1 The delivery workflow — follow this for every unit of work

Start from the contract and the user-visible behaviour. The sequence is a default workflow; an existing implementation may be inspected first when debugging or refactoring.

| # | Step | Output | Rule |
|---|---|---|---|
| 1 | **Read the contract.** Find the entity in `src/types/` and the endpoint in the generated API types. | Understanding of the shapes that already exist | CS-T-01 |
| 2 | **Model the domain.** Reuse generated/domain types and add a feature type only when it expresses a distinct view model or state. | Generated, domain, or colocated type | CS-T-02 |
| 3 | **Search `src/components/ui/` for an existing primitive.** Button, Input, Modal, Badge, Spinner already exist. | Either a reused import, or a deliberate decision to add a primitive | CS-U-01 |
| 4 | **Search `src/features/` and `src/hooks/` for existing logic.** Query hooks, formatters and guards are shared, not re-derived. | Either a reused import, or a new shared hook | CS-R-01 |
| 5 | **Implement the smallest coherent change.** Keep rendering, orchestration and domain logic separated where that separation improves clarity. | Feature code | CS-C-06 |
| 6 | **Add or update tests.** Prefer test-first for bugs and business rules; test observable behaviour, not implementation. | Adjacent unit/integration test | CS-Q-01 |
| 7 | **Run the repository-defined gates.** Type-check, lint, test, format and build as applicable. Zero warnings. | Green | CS-Q-08 |

> Reviewers verify reuse by checking the diff and repository search. Do not create an abstraction solely to satisfy this workflow: two pieces of code that look similar can represent different concepts.

### 0.2 What this document does not cover

| Not here | Where it lives |
|---|---|
| Which screens exist and what they do | TRD §7.1 — restated here as a route/feature/role map in §23.1, which is derived from it and never extends it |
| What the product may never build | RULE_BOOK §4 · TRD §7.4 "Components that must not be built" |
| API endpoint shapes | TRD §10 · generated OpenAPI types |
| Backend / edge-agent Python standards | *(separate document — not yet written)* |
| Visual design, spacing scale, colour tokens | Design tokens file `src/styles/tokens.css` |

---

## 1. The non-negotiables

If you read nothing else, read this table. Everything below is elaboration.

| ID | Rule |
|---|---|
| **CS-T-02** | **Contract first.** Reuse generated and domain types. Keep a type close to its owner; promote it only when it has multiple consumers. |
| **CS-T-05** | **Unsafe type escapes are exceptional.** `any`, unchecked assertions, non-null assertions and TypeScript suppression comments require a narrow scope and documented reason. Prefer `unknown`, validation and narrowing. |
| **CS-C-01** | **Exports are named and consistently declared.** Components use named `const` declarations; ordinary functions may use declarations when hoisting or readability helps. No `React.FC`. |
| **CS-U-01** | **Never build a second button.** Anything visual that appears twice lives in `src/components/ui/` and is imported. Features compose primitives; they do not re-implement them. |
| **CS-R-01** | **Reuse concepts, not text.** Share established primitives and domain rules; extract other duplication when the repeated code has the same meaning and a stable API. |
| **CS-G-01** | **Validate at trust boundaries.** Do not repeatedly check a value already guaranteed by a validated internal contract. Handle genuine domain absence and external mutation honestly. |
| **CS-D-01** | **All server state goes through TanStack Query.** No `fetch` in a component, no `useEffect` data loading, no state duplicated out of the query cache. |
| **CS-C-06** | **Separate responsibilities deliberately.** Split orchestration from presentation when either is non-trivial or independently reusable/testable. |
| **CS-A-01** | **Keyboard-first and never colour-alone.** NFR-ACC-01 and NFR-ACC-02 are product requirements, not polish. |
| **CS-SEC-03** | **The frontend is never an authorisation boundary.** Hidden controls and route guards shape navigation only. The server is authoritative for identity, permission and every Rule Book constraint. |
| **CS-B-01** | **The UI enforces the Rule Book.** No bulk actions, no per-person views, no auto-dispose, no escalation. These are absent by construction, not hidden by a flag. |

---

## 2. Project structure

Feature-first, not type-first. Code that changes together lives together.

```
web/
├── src/
│   ├── app/                        # Composition root — nothing else imports downward into features
│   │   ├── App.tsx                 # Provider tree only
│   │   ├── router.tsx              # Route table
│   │   └── providers/              # QueryClientProvider, AuthProvider, ErrorBoundary
│   │
│   ├── components/
│   │   ├── ui/                     # THE PRIMITIVES LAYER — zero domain knowledge
│   │   │   ├── Button/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Button.types.ts
│   │   │   │   ├── Button.test.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Input/  Select/  Modal/  Badge/  Spinner/  Table/  Toast/  Pagination/
│   │   │   └── index.ts            # Single barrel for the primitives layer
│   │   └── layout/                 # AppShell, SideNav, PageHeader, AdminLayout — domain-aware, feature-agnostic
│   │
│   ├── features/                   # One directory per bounded slice of the product
│   │   ├── auth/                   # SCR-1 Login, session bootstrap, sign-out — §23.3
│   │   ├── review-queue/
│   │   │   ├── api/                # Query + mutation hooks ONLY
│   │   │   │   ├── useQueueQuery.ts
│   │   │   │   ├── useSubmitDecision.ts
│   │   │   │   └── queryKeys.ts
│   │   │   ├── components/         # Feature-local components
│   │   │   ├── hooks/              # Feature-local non-server logic
│   │   │   ├── types.ts            # Feature-owned view models and state types, when needed
│   │   │   ├── constants.ts
│   │   │   └── index.ts            # The feature's PUBLIC surface. Cross-feature imports use this only.
│   │   ├── event-history/  rejection-log/  reports/
│   │   └── admin/                  # Grouping directory only — no barrel of its own (CS-F-04)
│   │       └── cameras/  zones-rules/  retention/  users/  audit-log/  system-health/
│   │                               # SCR-7…SCR-12 — each is a feature with its own api/, components/, index.ts (§23.5)
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts           # Single configured HTTP client. The only place fetch is called.
│   │   │   ├── schemas.ts          # Runtime schemas derived from the OpenAPI contract — the trust boundary
│   │   │   └── generated.ts        # openapi-typescript output. NEVER hand-edited.
│   │   ├── queryClient.ts
│   │   ├── env.ts                  # The only module that reads import.meta.env — CS-ENV-01
│   │   ├── format/                 # formatTimestamp, formatConfidence — pure, tested
│   │   └── utils/                  # cn(), assertNever(), invariant()
│   │
│   ├── hooks/                      # Genuinely global hooks: useAuth, useKeyboardShortcut, useSessionDraft
│   ├── types/                      # Cross-feature domain types: Event, Camera, Zone, Reviewer, Decision
│   ├── constants/                  # Routes, roles, event statuses, keyboard bindings, query settings
│   ├── styles/                     # tokens.css, index.css
│   └── test/                       # setup, render helpers, MSW handlers, factories
│
├── tsconfig.json
├── eslint.config.js
└── vite.config.ts
```

### 2.1 Structural rules

| ID | Rule | Why |
|---|---|---|
| **CS-F-01** | A feature may import from `components/ui`, `components/layout`, `lib`, `hooks`, `types`, `constants` — and from another feature **only via that feature's `index.ts`**. | Keeps the public surface of each slice small and refactorable. |
| **CS-F-02** | `components/ui` imports only peer primitives, `lib/utils` and `styles`. **It must never import from `features/` or domain `types/`.** Use direct peer imports internally to avoid barrel cycles. | A primitive that knows about `Event` is not a primitive. |
| **CS-F-03** | One exported component per file. Small private helpers may remain when they are inseparable from that component. The filename equals the export name. | Discoverability without needless file fragmentation. |
| **CS-F-04** | Barrel `index.ts` files define intentional public APIs at `components/ui/` and feature roots. Do not add nested or catch-all barrels. | Reduces import cycles and keeps ownership explicit. |
| **CS-F-05** | Nothing in `app/` is imported by anything else. It is the top of the graph. | Composition root. |
| **CS-F-06** | Imports use the `@/` alias for anything outside the current directory. No `../../../`. | Survives file moves. |
| **CS-F-07** | Colocate focused unit tests with their subject. Keep cross-feature integration and E2E tests in dedicated test directories. | Test location reflects test scope. |
| **CS-F-08** | A new `features/` directory is created when a slice owns its own screens, API surface and vocabulary — usually one row of TRD §7.1 or a coherent group of them. Do not create a feature for a single component; do not accumulate unrelated screens into one feature because they happen to render nearby. | The feature boundary is a domain boundary, not a folder-tidying exercise. |

---

## 3. Types and contracts

This is the section the rest of the document depends on. Guardian Lens is a system whose correctness claims are structural (RULE_BOOK §4). The type system is where those claims are made unmissable in the frontend.

### 3.1 Contract-first workflow

| ID | Rule |
|---|---|
| **CS-T-01** | Wire types — anything crossing the network — are **generated** from `/api/v1/openapi.json` into `lib/api/generated.ts` via `openapi-typescript`. They are never hand-written and never hand-edited. Regenerate when the contract changes; a failing `tsc` after regeneration is the contract drift the TRD §3 chose TypeScript to catch. |
| **CS-T-02** | Prefer generated wire types and shared domain types. Put feature-wide view models in `types.ts`; keep a single-use props type in the adjacent `.types.ts`. Do not create a placeholder `types.ts` for a feature that needs no new types. |
| **CS-T-03** | A type used by more than one feature is promoted to `src/types/` in the same commit that creates the second usage. |
| **CS-T-04** | Exported or reused types live in a `.types.ts` or feature `types.ts`. A short, private props type may stay beside a small component; extract it when it is exported, reused or obscures the render logic. |

### 3.2 The rules of typing

| ID | Rule | Example |
|---|---|---|
| **CS-T-05** | `any`, assertions, `!` and suppression comments are denied by default. A necessary interop escape must be minimal, documented, tested and linked to an issue when temporary. `as const` and `satisfies` are safe narrowing tools, not escape hatches. | Use `unknown` + validation/narrowing at boundaries. |
| **CS-T-06** | Use either `interface` or `type` consistently within a module. Prefer `type` for unions/mapped types and `interface` where declaration merging is intentionally required. | Avoid style-only review churn. |
| **CS-T-07** | Use closed literal unions for finite domain values. Use `string` for genuinely open text such as names, descriptions and server messages. Derive finite values from the API contract where possible. | `type EventStatus = 'unverified' \| 'accepted' \| 'corrected' \| 'rejected' \| 'expired'` |
| **CS-T-08** | **Discriminated unions instead of optional-field soup.** If two optional fields must appear together, they are not optional — they are a variant. | See §3.4 |
| **CS-T-09** | No `enum`. Use `as const` objects plus a derived union type. | See §3.3 |
| **CS-T-10** | Exported domain functions and stable library APIs declare return types. Framework adapters and hooks may use clear, non-leaking inference when spelling the framework type would add noise. | `export const describeDecision = (...): string => …` |
| **CS-T-11** | Derive, don't restate. Use `Pick`, `Omit`, `Extract`, `Parameters`, `ReturnType` rather than retyping a shape that already exists. | `type EventSummary = Pick<Event, 'id' \| 'status' \| 'occurredAt'>` |
| **CS-T-12** | Use `satisfies` for const config objects so keys stay checked and values stay narrow. | `const ROUTES = { … } satisfies Record<RouteKey, string>` |
| **CS-T-13** | Reusable/exported props are named `<Component>Props` and exported. Handlers are named `on<Event>`; the local implementation is `handle<Event>`. | `onDecision` prop, `handleDecision` local |
| **CS-T-14** | Exhaustively handle discriminated unions. Use `assertNever` where a runtime failure is safer than silent fall-through; otherwise rely on `switch-exhaustiveness-check` and an explicit return type. | See §3.5 |
| **CS-T-15** | No optional prop that a caller must always pass. Optional means "genuinely omittable, with a defined default". | — |

### 3.3 Constants and derived unions

```ts
// src/constants/events.ts
export const EVENT_STATUS = {
  UNVERIFIED: 'unverified',
  ACCEPTED:   'accepted',
  CORRECTED:  'corrected',
  REJECTED:   'rejected',
  EXPIRED:    'expired',
} as const;

export type EventStatus = (typeof EVENT_STATUS)[keyof typeof EVENT_STATUS];

// Keyboard bindings are a product requirement (TRD §7.4, NFR-ACC-01) — not a magic string.
export const DECISION_KEY = {
  ACCEPT:  'a',
  REJECT:  'r',
  CORRECT: 'c',
} as const;
```

### 3.4 Discriminated unions over optional fields

A `Decision` carries a reason only when it is a rejection, and a correction payload only when it is a correction (RULE_BOOK D3). Encode that.

```ts
// ✘ WRONG — every consumer must now guess which combinations are legal,
//   and every consumer writes its own defensive check to find out.
interface Decision {
  type: 'accept' | 'reject' | 'correct';
  reason?: string;
  correctedField?: string;
  correctedValue?: string;
}

// ✔ RIGHT — illegal states are unrepresentable. No runtime check needed.
export type Decision =
  | { readonly type: 'accept' }
  | { readonly type: 'reject'; readonly reason: RejectionReason }
  | { readonly type: 'correct'; readonly correction: FieldCorrection };
```

> This is CS-G-01 (no unnecessary checks) and CS-T-08 (discriminated unions) being the same rule seen from two directions. **You avoid runtime checks by making the illegal state impossible, not by remembering to check for it.**

### 3.5 Exhaustiveness

```ts
// src/lib/utils/assertNever.ts
export const assertNever = (value: never): never => {
  throw new Error(`Unhandled variant: ${JSON.stringify(value)}`);
};
```

```ts
export const describeDecision = (decision: Decision): string => {
  switch (decision.type) {
    case 'accept':  return 'Accepted';
    case 'reject':  return `Rejected — ${decision.reason.label}`;
    case 'correct': return `Corrected — ${decision.correction.field}`;
    default:        return assertNever(decision);
  }
};
```

Add a sixth event status and the compiler names every file that must change. That is the property worth the ceremony.

---

## 4. Components

### 4.1 Declaration

| ID | Rule |
|---|---|
| **CS-C-01** | Components use named `const` exports and typed props. Destructure props when it improves clarity; keep a `props` object when forwarding or distinguishing similarly named values. |
| **CS-C-02** | **No `React.FC` / `React.FunctionComponent`.** Declare `children: ReactNode` explicitly when the component accepts children. |
| **CS-C-03** | **No default exports** anywhere except `vite.config.ts` and `eslint.config.js`. Named exports keep imports greppable and renames honest. Lazy routes use `lazy(() => import('@/features/x').then((m) => ({ default: m.XPage })))`. |
| **CS-C-04** | Type imports use `import type { … }`. |
| **CS-C-05** | Keep components focused. Treat roughly 150 lines, high cognitive complexity or multiple independent responsibilities as review signals—not automatic extraction targets. |
| **CS-C-06** | Separate orchestration from presentation when either side is non-trivial or independently reusable/testable. A small route or leaf component may call a feature hook directly; it must not contain domain transformations that belong in a service or hook. |
| **CS-C-07** | Prefer a small, cohesive prop surface. A growing prop count is a design signal, but do not hide unrelated values in a generic object merely to reduce the count. Spread props only onto the intended native primitive. |
| **CS-C-08** | Keep JSX shallow enough to scan. Extract a named subcomponent when nesting represents a distinct concept, repeats, or makes behaviour hard to test. |
| **CS-C-09** | No inline function definitions of more than one expression inside JSX. Extract to a named `handleX` above the return. |
| **CS-C-10** | Use early returns for page-level loading, error and empty branches. Do not use nested ternaries in JSX; a simple two-way leaf ternary is acceptable. |
| **CS-C-11** | `key` is a stable domain id. **Never the array index.** |
| **CS-C-12** | No business logic in JSX. Compute above the return, into a named const. |

### 4.2 Anatomy — the fixed order inside a component file

```tsx
// 1. Imports: react → external packages → @/ internal → relative → type-only
import { useCallback } from 'react';

import { Button } from '@/components/ui';
import { DECISION_KEY } from '@/constants/events';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';

import type { DecisionBarProps } from '../types';

// 2. The component — one per file
export const DecisionBar = ({ disabled, onDecide }: DecisionBarProps) => {
  // 2a. Hooks — all of them, unconditionally, at the top
  // 2b. Handlers
  const handleAccept = useCallback(() => onDecide({ type: 'accept' }), [onDecide]);

  // 2c. Effects / subscriptions
  useKeyboardShortcut(DECISION_KEY.ACCEPT, handleAccept, { enabled: !disabled });

  // 2d. Derived values
  const accessibleLabel = disabled ? 'Loading evidence frame' : 'Accept candidate';

  // 2e. Render — early returns first, single JSX tree last
  return (
    <div role="group" aria-label="Decision actions">
      <Button variant="primary" onClick={handleAccept} disabled={disabled} aria-label={accessibleLabel}>
        Accept <kbd>A</kbd>
      </Button>
      {/* … */}
    </div>
  );
};
```

> `disabled` here is not cosmetic: the decision actions stay disabled until the evidence frame has rendered (CS-P-05, TRD §7.4). A decision recorded against a frame the reviewer has not seen is a BR-004 failure.

### 4.3 Worked example — the rules applied

```tsx
// ✘ WRONG — inline types, defensive noise, index keys, logic in JSX, magic strings,
//   a hand-rolled button, and a view that fetches.
export default function QueueList(props: any) {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    fetch('/api/v1/events?status=unverified')
      .then((r) => r.json())
      .then((d) => setEvents(d));
  }, []);

  if (!events) return null;
  if (!events.length) return null;

  return (
    <div>
      {events && events.map((e: any, i: number) => (
        <div key={i} onClick={() => props.onSelect && props.onSelect(e?.id)}>
          <span style={{ color: e.status === 'unverified' ? 'orange' : 'green' }}>
            {e?.status?.toUpperCase()}
          </span>
          <button className="px-3 py-1 rounded bg-blue-600 text-white">Review</button>
        </div>
      ))}
    </div>
  );
}
```

```tsx
// ✔ RIGHT — container fetches, view renders, types imported, primitives reused.

// features/review-queue/components/QueueListContainer.tsx
export const QueueListContainer = ({ onSelect }: QueueListContainerProps) => {
  const filters = useQueueFilters();                 // filters live in the URL — CS-RT-03
  const { data, isPending, isError, refetch } = useQueueQuery(filters);

  if (isPending) return <QueueSkeleton />;
  if (isError) return <ErrorState onRetry={refetch} />;
  if (data.items.length === 0) return <EmptyQueue />;

  return <QueueList items={data.items} depth={data.total} onSelect={onSelect} />;
};

// features/review-queue/components/QueueList.tsx
export const QueueList = ({ items, depth, onSelect }: QueueListProps) => (
  <section aria-label="Review queue">
    <QueueDepthBadge depth={depth} />   {/* Depth always visible — DP-4 */}
    <ul className="divide-y divide-border">
      {items.map((item) => (
        <QueueRow key={item.id} item={item} onSelect={onSelect} />
      ))}
    </ul>
  </section>
);
```

Note what disappeared: the null checks (the type says `items` is an array), the `&&` guards, the `?.` chains, the bespoke button, the inline colour logic, and the fetch. Nine lines of ceremony removed by getting the types and the layering right.

---

## 5. The shared UI layer — `components/ui/`

This is the section that answers "a common button used in every file". The primitives layer is not a convenience; it is the mechanism by which the codebase stays one codebase.

### 5.1 Rules

| ID | Rule |
|---|---|
| **CS-U-01** | Reuse an existing primitive before creating UI. Promote a repeated, domain-neutral pattern when its API is understood; do not generalise coincidental visual similarity. There is one canonical implementation of core controls such as buttons, inputs and modals. |
| **CS-U-02** | Primitives are **domain-blind**. No `Event`, `Camera`, `Reviewer` type may appear in `components/ui/`. A `StatusChip` that imports `EventStatus` belongs in `components/`, not `components/ui/`. |
| **CS-U-03** | A primitive that wraps one native element extends the appropriate native props without overriding them unsafely. Composite primitives expose a deliberate API and forward relevant accessibility attributes. |
| **CS-U-04** | Variants are a closed union typed in `<Component>.types.ts` and resolved through a lookup record — never through string concatenation or conditional class chains. |
| **CS-U-05** | Primitives forward refs and preserve accessibility attributes. A primitive that swallows `aria-*` is broken. |
| **CS-U-06** | **No raw `<button>`, `<input>`, `<select>` or `<textarea>` in a feature file.** ESLint enforces this (§21.2). |
| **CS-U-07** | Every primitive tests the behaviours it owns: semantics, keyboard/focus behaviour, disabled/loading state and relevant variants. Do not assert private class strings unless the class is the behaviour under test. |

### 5.2 The reference primitive

```ts
// components/ui/Button/Button.types.ts
import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  readonly isLoading?: boolean;
  readonly children: ReactNode;
}
```

```tsx
// components/ui/Button/Button.tsx
import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';
import { Spinner } from '@/components/ui/Spinner';

import type { ButtonProps, ButtonSize, ButtonVariant } from './Button.types';

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:   'bg-brand-600 text-white hover:bg-brand-700 focus-visible:ring-brand-500',
  secondary: 'bg-surface-2 text-fg border border-border hover:bg-surface-3',
  danger:    'bg-danger-600 text-white hover:bg-danger-700 focus-visible:ring-danger-500',
  ghost:     'bg-transparent text-fg hover:bg-surface-2',
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
};

const BASE_CLASS =
  'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ' +
  'disabled:pointer-events-none disabled:opacity-50';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading = false, disabled, className, children, ...rest }, ref) => (
    <button
      ref={ref}
      type="button"
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      className={cn(BASE_CLASS, VARIANT_CLASS[variant], SIZE_CLASS[size], className)}
      {...rest}
    >
      {isLoading ? <Spinner size="sm" aria-hidden /> : null}
      {children}
    </button>
  ),
);

Button.displayName = 'Button';
```

> The `Record<Variant, string>` lookup is the pattern. Add a variant to the union and TypeScript fails until the class map is complete. That is CS-T-14's exhaustiveness applied to styling.
>
> `disabled || isLoading` is deliberate. `disabled ?? isLoading` would leave the button live during a request whenever a caller passes `disabled={false}` explicitly — a double-submit path on the decision endpoint.

### 5.3 Primitive roadmap

Likely primitives include `Button`, `IconButton`, `Input`, `PasswordInput`, `Textarea`, `Select`, `Checkbox`, `Radio`, `Label`, `FormField`, `Modal`, `Badge`, `Spinner`, `Skeleton`, `Table`, `Pagination`, `Tabs`, `Breadcrumb`, `Toast`, `Tooltip`, `EmptyState`, `ErrorState` and `Card`.

`Pagination` is not optional furniture: every list surface in the product is server-paged (§9.5), so it is built once, keyboard-operable and announced, and never re-implemented per screen.

Build a primitive when a feature needs it, starting with controls used by the critical review flow. Do not build the entire catalogue speculatively. Each primitive must ship with its accessibility behaviour, types and tests.

---

## 6. Reuse and duplication

| ID | Rule |
|---|---|
| **CS-R-01** | Share established UI primitives and domain rules immediately. For other code, remove duplication when the repeated code represents the same concept and a stable shared API is visible. |
| **CS-R-02** | **Incidental similarity follows the rule of three.** Two functions that look alike but answer different questions stay separate until a third proves the shared concept. Premature abstraction — a hook with five boolean flags to serve three callers — is worse than the duplication it removed. |
| **CS-R-03** | Extract repeated non-trivial domain expressions into the owning feature or domain module. Use `lib/` only for genuinely cross-feature, domain-neutral code. |
| **CS-R-04** | Name values whose meaning or policy is not obvious: durations, limits, routes, storage keys and query settings. Literal `0`, `1`, empty strings and one-off display copy do not need ceremonial constants. `QUEUE_POLL_INTERVAL_MS` is better than an unexplained `15_000`. |
| **CS-R-05** | Repeated Tailwind sequences become a component or variant when they represent one UI concept. Do not move class strings into constants merely to reduce textual duplication. |
| **CS-R-06** | Before adding a util, grep `lib/`. Duplicate `formatDate` implementations are a review-blocking defect. |
| **CS-R-07** | A shared abstraction takes data and returns data. It does not take a `mode` flag that switches its behaviour wholesale — that is two functions wearing one name. |

---

## 7. State and hooks

State placement follows TRD §7.3 exactly. It is settled; do not re-litigate it in code.

| Concern | Mechanism | Rule |
|---|---|---|
| Server state | **TanStack Query** | CS-D-01 |
| Filters, sort, pagination, selection | **The URL** | CS-RT-03 |
| Auth / current principal | `AuthContext` + refresh interceptor | CS-S-05 |
| Draft decision in progress | Local state, mirrored to `sessionStorage` | CS-S-06 |
| UI preferences | `localStorage` via `useLocalStorage` | — |
| Global store (Redux/Zustand/MobX) | **Not used.** TRD §7.3. Introducing one is a TRD change, not a refactor. | CS-S-07 |

### 7.1 Rules

| ID | Rule |
|---|---|
| **CS-S-01** | State lives at the lowest common ancestor that needs it. Lift only when a second consumer appears. |
| **CS-S-02** | **Never store derived state.** If it can be computed from props or query data, compute it in render. `useEffect` + `setState` to mirror a prop is banned. |
| **CS-S-03** | **`useEffect` is for synchronising with something outside React**—subscriptions, event listeners, timers or imperative browser APIs. Not for fetching or deriving state. A non-obvious effect should explain the external system and cleanup requirement. |
| **CS-S-04** | Group state by transition, not by an arbitrary count. Use separate values for independent changes and `useReducer` when named events govern related state transitions. |
| **CS-S-05** | Context holds stable, rarely-changing values (auth, theme). Never put fast-changing state in context. |
| **CS-S-06** | Custom hooks are named `use<Thing>`, live in `hooks/` (global) or `features/<f>/hooks/` (local), return a typed object — never a positional tuple beyond two elements — and are tested. |
| **CS-S-07** | No global store. See table above. |
| **CS-S-08** | **No premature memoization.** Add `useMemo`, `useCallback` or `memo` for a measured cost, referential stability required by an API/hook, or a clearly expensive calculation. Document non-obvious performance work with evidence. |

---

## 8. Routing and URL state

The reviewer's working position — which filter, which page, which candidate — is part of their task state, not an implementation detail. Losing it on a refresh costs them the queue position they were holding in their head.

| ID | Rule |
|---|---|
| **CS-RT-01** | Routes are declared once in `app/router.tsx` and referenced through typed constants in `constants/routes.ts`. No path string literals in components; build parameterised paths through a helper so a route rename is a compile error. |
| **CS-RT-02** | Route params and query strings are external input (CS-G-13). Parse and validate them at the route boundary and pass typed values inward. A malformed param renders a not-found or error state — never a crash, and never a request with `undefined` interpolated into the URL. |
| **CS-RT-03** | **Filters, sort, pagination and the selected candidate live in the URL**, not in component state. Reload, back-button and link-sharing must all preserve position. These parsed values feed the query key directly (CS-D-03), which makes the cache entry and the address bar the same fact. |
| **CS-RT-04** | Routes are code-split by default (`lazy` + `Suspense` with a route-level fallback). The review queue may be eagerly bundled — TRD §7.2 makes it the application's home and it is the screen whose first paint matters. |
| **CS-RT-05** | Every route sits inside an error boundary (CS-G-17) and unknown paths render an explicit not-found screen. |
| **CS-RT-06** | Route guards shape navigation only; they are never the authorisation boundary (CS-SEC-03). The API enforces access and the UI handles `401` and `403` distinctly (CS-D-13). |
| **CS-RT-07** | On navigation, set the document title and move focus to the main heading. Without this a keyboard or screen-reader user has no signal that the page changed — NFR-ACC-01. |
| **CS-RT-08** | State that must survive a token refresh mid-decision belongs in `sessionStorage` (CS-S-06), not in router location state, which is lost on a hard reload. |

---

## 9. Data layer

### 9.1 Rules

| ID | Rule |
|---|---|
| **CS-D-01** | All server state flows through TanStack Query. **`fetch` is called in exactly one file: `lib/api/client.ts`.** |
| **CS-D-02** | Every endpoint has a hook in `features/<f>/api/`. Components call hooks; they never call the client directly. |
| **CS-D-03** | Query keys come from a **key factory** per feature. Never an inline array literal. |
| **CS-D-04** | Untrusted API data is validated at the client boundary with a runtime schema generated from, or checked against, the OpenAPI contract. Do not maintain unrelated TypeScript and Zod definitions of the same shape. Everything downstream consumes the validated type. |
| **CS-D-05** | Mutations invalidate precisely — the affected keys, not the whole cache. |
| **CS-D-06** | Optimistic updates implement `onMutate` snapshot → `onError` rollback → `onSettled` invalidate (TRD §7.3). Prefer a pessimistic mutation when rollback cannot faithfully restore state or the user must see authoritative server confirmation. |
| **CS-D-07** | Loading, error and empty are three distinct rendered states. Never one spinner covering all three. |
| **CS-D-08** | Errors surface a human-readable message and a recovery action. A silent `catch` is a review-blocking defect. |
| **CS-D-09** | Poll intervals, stale times and retry counts come from `constants/query.ts` — not scattered literals. TRD §17: queue stale time 15 s. |
| **CS-D-10** | Pass TanStack Query's `AbortSignal` through the API client so superseded requests are cancelled. Effects and manual async work must also clean up subscriptions and requests. |
| **CS-D-11** | Retry only transient failures on safe/idempotent operations, with bounded backoff. Do not automatically retry a decision mutation unless the endpoint has an explicit idempotency contract. |
| **CS-D-12** | The API client maps transport and API error envelopes into one typed application error. Preserve correlation IDs for support, but show users safe, actionable copy rather than stack traces or raw payloads. |
| **CS-D-13** | Authentication refresh is single-flight and attempted at most once per failed request. Handle `401`, `403` and decision `409` distinctly; a conflict refreshes authoritative event state rather than overwriting it. |

> **On the decision mutation specifically.** TRD §7.3 calls for optimistic update with rollback, and the optimistic scope is deliberately narrow: remove the decided candidate from the queue list so the reviewer moves on immediately. **Never optimistically render a verified record, a count or a report entry** — until the server confirms, no Verified Record exists (BR-004), and showing one is the product claiming a fact it does not hold.

### 9.2 Key factory

```ts
// features/review-queue/api/queryKeys.ts
import type { QueueFilters } from '../types';

export const queueKeys = {
  all:      ['queue'] as const,
  lists:    () => [...queueKeys.all, 'list'] as const,
  list:     (filters: QueueFilters) => [...queueKeys.lists(), filters] as const,
  details:  () => [...queueKeys.all, 'detail'] as const,
  detail:   (eventId: string) => [...queueKeys.details(), eventId] as const,
} as const;
```

### 9.3 Query hook

```ts
// features/review-queue/api/useQueueQuery.ts
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api/client';
import { queuePageSchema } from '@/lib/api/schemas';
import { QUEUE_POLL_INTERVAL_MS, QUEUE_STALE_TIME_MS } from '@/constants/query';

import { queueKeys } from './queryKeys';
import type { QueueFilters, QueuePage } from '../types';

export const useQueueQuery = (filters: QueueFilters) =>
  useQuery<QueuePage>({
    queryKey: queueKeys.list(filters),
    queryFn: async ({ signal }) => {
      const raw = await apiClient.get('/api/v1/events', { params: filters, signal });
      return queuePageSchema.parse(raw); // The only shape check in the whole flow.
    },
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: QUEUE_POLL_INTERVAL_MS,
    refetchIntervalInBackground: false, // CS-P-07
  });
```

### 9.4 Mutation with rollback

```ts
// features/review-queue/api/useSubmitDecision.ts
export const useSubmitDecision = (eventId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (decision: Decision) =>
      apiClient.post(`/api/v1/events/${eventId}/decision`, decision),

    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queueKeys.lists() });
      const previous = queryClient.getQueriesData<QueuePage>({ queryKey: queueKeys.lists() });
      queryClient.setQueriesData({ queryKey: queueKeys.lists() }, removeEvent(eventId));
      return { previous };
    },

    onError: (_error, _decision, context) => {
      // Rollback is mandatory — CS-D-06. A decision that appears to have
      // succeeded when it did not is a BR-004 integrity failure, not a UI glitch.
      context?.previous.forEach(([queryKey, data]) => {
        queryClient.setQueryData(queryKey, data);
      });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queueKeys.all });
    },
  });
};
```

### 9.5 Pagination

Every list in this product is a **server-paged, cursor-based** list. TRD §10.1 fixes the contract — `?limit=&cursor=` — and it is cursor-based deliberately: the review queue moves while the reviewer works it, and offset paging over a moving dataset silently skips and repeats rows. A skipped row in this product is a candidate event nobody ever saw.

| ID | Rule |
|---|---|
| **CS-PG-01** | **Paging is cursor-based, always.** The client sends `limit` and an opaque `cursor` and follows the server's `next_cursor`. No page numbers are computed, no offset is constructed, and no total page count is displayed unless the API returns one. A "Page 7 of 42" the server never asserted is an invented fact. |
| **CS-PG-02** | The cursor is **opaque**. Never decode, parse, increment, slice or persist it beyond the URL and the query key. It is a server token, not a client value. |
| **CS-PG-03** | **Pagination state lives in the URL** (`?limit=&cursor=`), with filters, sort and selection — CS-RT-03. Refresh, back and a shared link return the reviewer to the same page of the same list. Component state that holds a cursor is a bug: it dies on reload and takes the reviewer's position with it. |
| **CS-PG-04** | `limit` and `cursor` are external input (CS-G-13). Parse them at the route boundary: an unparseable or out-of-range `limit` falls back to `DEFAULT_PAGE_SIZE` rather than being forwarded; a rejected cursor (`400`/`422`) resets to the first page and states why. Never issue a request with `cursor=undefined` interpolated into it. |
| **CS-PG-05** | Page size comes from `constants/query.ts` — `DEFAULT_PAGE_SIZE` and `PAGE_SIZE_OPTIONS`. No literal `20` in a hook. A screen that offers a page-size control writes the chosen value to the URL and resets the cursor. |
| **CS-PG-06** | **Changing a filter, sort or page size resets the cursor to the first page in the same URL update.** A cursor is only valid for the query that produced it; sending yesterday's cursor with today's filters asks the server a question it cannot answer honestly. |
| **CS-PG-07** | The cursor and limit are part of the query key (CS-D-03). The key factory takes them; a component never assembles a key literal to page. |
| **CS-PG-08** | **Queue depth is the server's total, not `items.length`.** The depth badge shows the whole backlog, never the current page's row count — DP-4, CS-B-08. `Showing 20 of 340` and `340 awaiting review` are different claims; render the one the API actually supports. |
| **CS-PG-09** | Paging keeps the previous page rendered with `aria-busy` while the next loads (`placeholderData: keepPreviousData`) and prefetches the next cursor when it is known. A table that blanks to a spinner on every page change costs the reviewer their place — DP-2. |
| **CS-PG-10** | **Explicit Next / Previous controls. No infinite scroll on evidence, record or audit surfaces.** A reviewer must be able to say which page they were on, and an auditor must be able to return to it. Where a load-more affordance is deliberately chosen for a specific list, the cursor is still mirrored to the URL and the total stays visible. |
| **CS-PG-11** | Polling refetches **the page currently displayed only**, and never auto-advances the page under the reviewer. When a decision empties the last row of a page, the reviewer is shown an explicit end-of-page state with a Next/Previous action — the UI does not jump pages on its own (DP-2, DP-4). |
| **CS-PG-12** | **No client-side paging, sorting, filtering or slicing across pages.** A page is a server answer; sorting the twenty rows in hand and calling it "sorted by time" misrepresents the dataset. Sort is a request parameter — CS-P-06, CS-P-08. |
| **CS-PG-13** | End-of-list is an explicit rendered state, distinct from empty (CS-D-07). `Next` at the end is disabled with `aria-disabled` **and** a stated reason; a dead control with no explanation is a dead end for a keyboard user who cannot hover. |
| **CS-PG-14** | Pagination renders through the `Pagination` primitive: a `<nav aria-label="Pagination">` of real buttons, keyboard-operable, ≥44×44 targets, with the current range announced via `aria-live` so a screen-reader user knows the page changed (CS-A-01, CS-A-06, CS-A-08). No feature hand-rolls Next/Previous buttons — CS-U-01. |
| **CS-PG-15** | Export and report generation are server operations over the **whole** filtered set, never over the page in hand. Exporting the current page while labelling it a report is a BR-R-01 misstatement. |

```ts
// features/event-history/api/queryKeys.ts — page params are part of the key, never appended ad hoc
export const historyKeys = {
  all:   ['history'] as const,
  lists: () => [...historyKeys.all, 'list'] as const,
  list:  (filters: HistoryFilters, page: PageParams) =>
    [...historyKeys.lists(), filters, page] as const,
} as const;

// features/event-history/api/useHistoryQuery.ts
export const useHistoryQuery = (filters: HistoryFilters, page: PageParams) =>
  useQuery<HistoryPage>({
    queryKey: historyKeys.list(filters, page),
    queryFn: async ({ signal }) => {
      const raw = await apiClient.get('/api/v1/events', {
        params: { ...filters, limit: page.limit, cursor: page.cursor },
        signal,
      });
      return historyPageSchema.parse(raw);
    },
    // CS-PG-09 — the table does not blank between pages.
    placeholderData: keepPreviousData,
  });
```

```ts
// features/event-history/hooks/useHistoryPaging.ts
// CS-PG-04 / CS-PG-06 — the URL is parsed once here and nothing downstream re-checks it.
export const useHistoryPaging = (): HistoryPaging => {
  const [params, setParams] = useSearchParams();

  const limit = parsePageSize(params.get('limit'));      // clamps to PAGE_SIZE_OPTIONS
  const cursor = params.get('cursor') ?? undefined;      // opaque — CS-PG-02

  const goToPage = (next: string | undefined) => setParams(withCursor(params, next));
  const applyFilters = (filters: HistoryFilters) =>
    setParams(withCursor(withFilters(params, filters), undefined)); // cursor reset — CS-PG-06

  return { page: { limit, cursor }, goToPage, applyFilters };
};
```

---

## 10. Forms and user input

Guardian Lens has few forms, and each is consequential. A rejection reason is mandatory (FR-043). A correction amends a record that becomes evidence carrying the reviewer's name (BR-005). Form defects here are record defects.

| ID | Rule |
|---|---|
| **CS-FM-01** | Forms use React Hook Form with a schema resolver. One schema per form, and the submitted value's type is **derived from that schema** — never a schema plus a separately hand-written type (CS-D-04's rule applied to input). |
| **CS-FM-02** | Validate on submit, then re-validate on change **after the first failed submit**. Validating every keystroke from the first character reports errors for input the user has not finished typing. |
| **CS-FM-03** | Every field error is programmatically associated with its input (`aria-invalid`, `aria-describedby`) and rendered as text. A red border is not an error message (CS-A-02). |
| **CS-FM-04** | On a failed submit, move focus to the first invalid field. For forms beyond a few fields, also render an error summary at the top of the form. |
| **CS-FM-05** | The submit control is disabled **while the request is in flight**, not while the form is invalid. A permanently disabled button with no stated reason is a dead end — especially for a keyboard user who cannot hover for a tooltip. |
| **CS-FM-06** | A failed submit never clears user input. Re-render with the entered values and map the server's field errors onto the matching fields; fall back to a form-level message where the API does not identify a field (CS-D-08, CS-D-12). |
| **CS-FM-07** | Mandatory means blocked, not nudged. The rejection reason is required by FR-043: there is no submit path that records a rejection without one, and no default or placeholder value that could stand in for a reviewer's words. |
| **CS-FM-08** | An in-progress decision draft persists to `sessionStorage` per TRD §7.3 and is cleared once the decision is recorded or abandoned. It is never written to `localStorage` — it concerns a candidate event and must not outlive the session (CS-SEC-07). |
| **CS-FM-09** | Forms are composed from the `FormField` primitive so label association, error rendering and required-marking are implemented once. A feature that hand-wires `<label htmlFor>` is re-implementing a primitive (CS-U-01). |

---

## 11. Defensive checks — what is required and what is noise

This section is the direct answer to "no unnecessary checks in code". The principle:

> **Validate once, at the boundary. Trust the type everywhere else. If you feel you need a guard inside the app, the type upstream is wrong — fix the type.**

### 11.1 Checks that are BANNED

| ID | Banned | Because |
|---|---|---|
| **CS-G-01** | `if (!prop) return null` where `prop` is typed non-nullable | The type already guarantees it. The check is dead code that hides a contract error rather than surfacing it. |
| **CS-G-02** | `?.` on a non-optional path — `event?.zone?.name` when both are required | Optional chaining on a required field advertises that you do not trust your own contract. |
| **CS-G-03** | `\|\| ''` / `?? ''` fallbacks on required strings | Turns a data bug into a silently blank UI. |
| **CS-G-04** | `Array.isArray(x)` / `typeof x === 'string'` on typed internal values | Runtime re-checking of a compile-time guarantee. |
| **CS-G-05** | `try/catch` around code that cannot throw | Noise. |
| **CS-G-06** | Redundant `x && x.length > 0 && x.map(…)` | `x.length === 0` is an explicit empty state (CS-D-07), not an inline `&&`. |
| **CS-G-07** | Defaulting a required prop inside the component | If it has a sensible default it is optional; if it does not, defaulting hides the bug. |

### 11.2 Checks that are REQUIRED

| ID | Required at | Mechanism |
|---|---|---|
| **CS-G-10** | **Every untrusted API response** | Parse at the API-client boundary with a runtime schema generated from or contract-checked against OpenAPI. Avoid scattering parsing through components and hooks. |
| **CS-G-11** | **Every user input** | Schema validation at submit (§10). Never trust a form field. |
| **CS-G-12** | `catch (error: unknown)` | Narrow before use. Never `catch (e: any)`. |
| **CS-G-13** | Route params, query strings, `localStorage` / `sessionStorage` reads | All are `string \| null` from the outside world — parse them (CS-RT-02). |
| **CS-G-14** | Array index access | `noUncheckedIndexedAccess` is on; the resulting `T \| undefined` is handled honestly, not asserted away with `!`. |
| **CS-G-15** | Discriminated union narrowing | Switch on the discriminant (§3.5). This is narrowing, not defensive checking. |
| **CS-G-16** | Genuine domain optionality | `Event.decidedAt` is legitimately absent while unverified. Model it optional and branch on it — that is a business rule (RULE_BOOK D3), not a defensive check. |
| **CS-G-17** | Route-level error boundary | One per route, plus a root boundary. Rendering failures are caught, logged and shown — never a white screen. |

### 11.3 The test

Before writing a check, ask: **"What type would make this check impossible to need?"** If such a type exists, write it instead. If the value genuinely arrives from outside the program — network, user, storage, URL, browser API — the check belongs there and only there.

---

## 12. Styling

| ID | Rule |
|---|---|
| **CS-Y-01** | Tailwind utilities only. **No inline `style` attribute** except for genuinely dynamic values a class cannot express (e.g. a computed bounding-box overlay position on the evidence frame). |
| **CS-Y-02** | No CSS modules, no styled-components, no `.css` files beyond `styles/tokens.css` and `styles/index.css`. |
| **CS-Y-03** | Class strings are composed with `cn()` (clsx + tailwind-merge). Never template-literal concatenation. |
| **CS-Y-04** | **No arbitrary values** (`h-[37px]`, `text-[#1a2b3c]`) outside the tokens file. Extend the Tailwind theme instead. Colours come from semantic tokens (`bg-surface-2`, `text-danger`), never raw palette values in a feature file. |
| **CS-Y-05** | Conditional classes resolve through a `Record<Variant, string>` lookup (§5.2), never a chain of ternaries. |
| **CS-Y-06** | Class order is enforced by `prettier-plugin-tailwindcss`. Do not hand-order. |
| **CS-Y-07** | Dark mode via the `dark:` variant on semantic tokens. Never a duplicated component. |
| **CS-Y-08** | Every interactive element has a visible `focus-visible` ring. Removing focus outlines is banned — NFR-ACC-01 depends on them. |

---

## 13. Formatting, time and units

A timestamp on an evidence frame is part of what a reviewer attests to when they accept a candidate (BR-005). Display ambiguity here is a record defect, not a cosmetic one.

| ID | Rule |
|---|---|
| **CS-FMT-01** | Timestamps cross the wire as ISO 8601 with an explicit offset and are held in state exactly as received. Do not parse into a local `Date` and pass that around; convert only at the point of display. |
| **CS-FMT-02** | Timestamps render in the **site's** timezone with the zone shown, through a single `formatTimestamp`. A reviewer in one timezone deciding on a frame captured in another must never have to work out which clock they are reading. |
| **CS-FMT-03** | Relative time ("3 minutes ago") may accompany an absolute timestamp; it never replaces one on an evidence or audit surface. |
| **CS-FMT-04** | Confidence renders through a single formatter at one fixed precision, always with its unit. `0.82` on one screen and `82%` on another asks the reviewer to do arithmetic to do their job — and confidence may inform their attention but never their decision (BR-V-03). |
| **CS-FMT-05** | Every formatter lives in `lib/format/`, is pure, and is unit-tested including boundary cases (midnight, DST transition, zero, exact threshold). Components never format inline. |
| **CS-FMT-06** | Durations, intervals and retention periods are stored and passed as explicit units in the identifier (`retentionDays`, `debounceMs`). A bare number is not a duration. |

---

## 14. Naming

| Subject | Convention | Example |
|---|---|---|
| Component file & export | `PascalCase` | `DecisionBar.tsx` → `DecisionBar` |
| Hook file & export | `camelCase`, `use` prefix | `useQueueQuery.ts` |
| Types file | `types.ts` (feature) · `X.types.ts` (primitive) | `Button.types.ts` |
| Util / service file | `camelCase` | `formatTimestamp.ts` |
| Directory | `kebab-case` | `features/review-queue/` |
| Type / interface | `PascalCase`, no `I` or `T` prefix | `QueueFilters`, not `IQueueFilters` |
| Props interface | `<Component>Props` | `DecisionBarProps` |
| Constant | `SCREAMING_SNAKE_CASE` | `QUEUE_POLL_INTERVAL_MS` |
| Boolean | `is` / `has` / `can` / `should` prefix | `isPending`, `canDecide` |
| Event handler prop | `on<Event>` | `onDecide` |
| Handler implementation | `handle<Event>` | `handleDecide` |
| Async function | Verb phrase, no `Async` suffix | `submitDecision` |

| ID | Rule |
|---|---|
| **CS-N-01** | Names use the vocabulary of RULE_BOOK §3.1 exactly. A candidate event is a `candidate` or `CandidateEvent` — never an `alert`, `violation`, `incident` or `flag`. **The words are the product; changing them changes what the code claims.** |
| **CS-N-02** | No abbreviations except the established set: `id`, `url`, `api`, `ui`, `db`, `ms`. Not `evt`, `cfg`, `usr`, `btn`. |
| **CS-N-03** | Names say what a thing is, not how it is implemented. `useQueue`, not `useQueueArrayFetcher`. |
| **CS-N-04** | User-facing copy obeys CS-N-01 too. A screen that labels a candidate "Violation" has made a claim the system is not entitled to make (BR-004) — in the one place a customer will actually read it. |

---

## 15. Accessibility

These are product requirements from the TRD, not a quality bonus. The reviewer clears the queue with a keyboard all day; if that is slow, the product fails on P-01.

| ID | Rule | Source |
|---|---|---|
| **CS-A-01** | Every action reachable and operable by keyboard. The decision path — navigate queue, open candidate, decide — is completable **without a mouse**. Bindings: `A` accept, `R` reject, `C` correct. | NFR-ACC-01 · TRD §7.4 |
| **CS-A-02** | **Status is never conveyed by colour alone.** Every `StatusChip` carries text or an icon in addition to colour. | NFR-ACC-02 · TRD §7.4 |
| **CS-A-03** | Semantic HTML first. `<button>` for actions, `<a>` for navigation, real headings in order, `<ul>` for lists. An ARIA role is a last resort, not a first choice. | — |
| **CS-A-04** | Every form control has an associated `<label>`. Placeholder is not a label. | — |
| **CS-A-05** | Modals trap focus, close on `Escape`, and restore focus to the trigger. Use the `Modal` primitive; do not hand-roll. | — |
| **CS-A-06** | Async state changes announce via `aria-live`. A reviewer must know a decision was recorded without watching for a visual flash. | — |
| **CS-A-07** | Images carry meaningful `alt`. Decorative images carry `alt=""`. The evidence frame's alt states camera, zone and timestamp. | — |
| **CS-A-08** | Text contrast ≥ 4.5:1; interactive targets ≥ 44×44 px. | — |
| **CS-A-09** | `eslint-plugin-jsx-a11y` runs at error level and `vitest-axe` asserts zero violations on screen-level tests. **Automated checks are a floor, not a ceiling** — they cannot detect a wrong focus order or an unreachable control. | — |
| **CS-A-10** | Every page provides a skip link to main content and uses landmark elements (`<main>`, `<nav>`, `<header>`). | — |
| **CS-A-11** | Keyboard shortcuts do not fire while focus is in a text field, and every shortcut has a visible affordance (the `<kbd>` hint on the decision buttons). An invisible shortcut is not a feature. | NFR-ACC-01 |
| **CS-A-12** | Animation respects `prefers-reduced-motion`. Nothing essential is conveyed by motion alone. | — |
| **CS-A-13** | Each release includes a manual keyboard-only pass of the full decision path. This is a release gate, not an automated test. | NFR-ACC-01 |

---

## 16. Performance and payload

The dominant cost in this application is not JavaScript — it is evidence frames, one per candidate, fetched while a reviewer waits. Optimise that, and measure everything else before touching it.

| ID | Rule |
|---|---|
| **CS-P-01** | Measure before optimising. A performance change lands with the measurement that motivated it recorded in the pull request (CS-S-08). |
| **CS-P-02** | Routes are code-split (CS-RT-04) and a bundle-size budget is a CI gate. Exceeding it fails the build; the budget is raised deliberately with a reason, never silently. |
| **CS-P-03** | Evidence frames declare intrinsic dimensions or sit in an aspect-ratio box, so the decision UI does not shift as the image lands. A layout shift under the reviewer's cursor mid-decision is a misclick risk, not a cosmetic issue. |
| **CS-P-04** | The frame for the candidate under review loads eagerly; off-screen frames load lazily; where queue order is known, the next frame is prefetched. Time spent waiting on an image is the reviewer's dominant per-item cost, and reviewer load is the product's stated abandonment risk (P-01). |
| **CS-P-05** | Decision actions enable only once the evidence frame has rendered — TRD §7.4. This is a correctness rule in performance clothing: a decision recorded against a frame the reviewer has not seen is a BR-004 failure. |
| **CS-P-06** | Prefer server-side pagination — already in the queue contract — to client-side windowing. Window a list only when its length is genuinely unbounded by the API. |
| **CS-P-07** | Polling pauses when the document is hidden. At the 15-second queue interval, a tab left open for a day issues 5,760 requests against a site that has gone home. |
| **CS-P-08** | No synchronous heavy work in render. Sorting, filtering and grouping happen in the query layer or a memoised selector with a measured cost behind it. |

---

## 17. The Rule Book in the UI

Some code must not exist. These rules are enforced by absence and by test — the frontend is one of the enforcement points listed in RULE_BOOK §6.

| ID | The UI must never contain | Rule |
|---|---|---|
| **CS-B-01** | Any control that decides more than one candidate in a single act—no bulk accept, no bulk reject and no "select all". The UI contains no such affordance; the API bypass suite separately proves that no bulk route exists. | BR-V-02 · FR-047 · DP-3 |
| **CS-B-02** | Any per-person view: dashboard, leaderboard, activity chart, worker filter, or any field that identifies a Worker. **No such field exists in the types.** | BR-002, BR-006 |
| **CS-B-03** | Any "notify HR", escalate-to-management, or consequence action. No such client exists in the integration layer. | BR-003, BR-N-01 |
| **CS-B-04** | Any confidence-based auto-dispose toggle. Confidence may **sort or annotate** the queue; it may never decide. | BR-V-03 · FR-048 |
| **CS-B-05** | Any client-supplied `reviewer_id`. Reviewer identity is derived server-side from the session; the client never sends it and no type field exists for it. | BR-S-01 |
| **CS-B-06** | Any UI that renders an unverified candidate inside a report, count or trend — including optimistically, before the server has confirmed a decision (CS-D-06). | BR-004, BR-R-01 |
| **CS-B-07** | Any edit affordance on a decided event. Decisions are immutable; correction is a new record. | BR-V-01 |
| **CS-B-08** | Queue depth hidden or collapsed. Depth is always visible. | DP-4 · TRD §7.4 |
| **CS-B-09** | Any rejection-count or acceptance-rate surface that is hidden, collapsed by default or gated behind a permission. The system's own error rate is visible to the customer. | BR-007, BR-R-03 |

> **How this is enforced:** test user-visible prohibitions at the UI level by asserting that forbidden affordances and data are absent. Enforce API/schema prohibitions in the TRD §19.4 bypass suite and with compile-time contract checks where appropriate. A test that merely checks a forbidden control is disabled is insufficient: **absent, not disabled.**
>
> These affordances are also not reachable by configuration. See CS-ENV-04.

---

## 18. Security and privacy

Frontend controls improve user experience but are never an authorisation boundary. The server remains authoritative for identity, permissions and every Rule Book constraint.

| ID | Rule |
|---|---|
| **CS-SEC-01** | Never place secrets, private keys, service credentials or privileged API tokens in frontend code, Vite environment variables, fixtures, logs or source maps. Anything shipped to the browser is public. |
| **CS-SEC-02** | Render untrusted text through React's normal escaping. `dangerouslySetInnerHTML`, direct DOM HTML injection and unsanitised rich text are banned. If a reviewed rich-text requirement appears, use an approved sanitizer and test hostile payloads. |
| **CS-SEC-03** | Do not make authorisation decisions from hidden buttons, route guards, local storage or decoded JWT claims. These may shape navigation only; the API must enforce access and the UI must handle `401` and `403`. |
| **CS-SEC-04** | Centralise authentication and request policy in the API client. Do not log tokens, passwords, evidence URLs, personal data or full error payloads. Error reporting uses allow-listed metadata and redaction. |
| **CS-SEC-05** | Treat URLs, route parameters, storage, `postMessage`, file input and clipboard contents as untrusted. Validate protocols and destinations; never navigate to or request an unchecked URL. |
| **CS-SEC-06** | Prefer secure, server-managed cookies for refresh credentials when architecture permits. If the TRD-required token design stores browser credentials, document the threat model and minimise lifetime and exposure. Never persist access tokens in `localStorage`. |
| **CS-SEC-07** | Evidence frames and sensitive responses must not be placed in shared caches or persisted client stores. Preserve the TRD cache policy (`private`) and clear sensitive client state on logout. |
| **CS-SEC-08** | Dependency changes require lockfile review, licence compatibility and automated vulnerability scanning. A finding is triaged by reachability and impact; severity alone neither proves nor dismisses risk. |
| **CS-SEC-09** | Do not weaken CSP, CORS, cookie attributes, TLS checks or sanitisation to make development convenient. Any exception requires a time-bounded security review and issue. |
| **CS-SEC-10** | Evidence frames are never downloaded, copied, printed or shared through an affordance the UI provides. Retention is enforced server-side (BR-009); a client-side copy escapes it entirely. |

---

## 19. Environment and configuration

| ID | Rule |
|---|---|
| **CS-ENV-01** | All environment access goes through a single typed module (`lib/env.ts`) that validates the complete set at startup. `import.meta.env` appears nowhere else in the codebase. |
| **CS-ENV-02** | A missing or malformed required variable fails the build or the boot, loudly. It must never degrade into a silent `undefined` that surfaces later as a request to `undefined/api/v1/events`. |
| **CS-ENV-03** | Everything in the frontend environment is public (CS-SEC-01). If a value must stay secret, the feature needs a server-side path — that is an architecture change raised to the TRD, not a frontend workaround. |
| **CS-ENV-04** | **A feature flag may defer a feature. It may never gate a Rule Book constraint.** Nothing forbidden by §17 becomes reachable by flipping a flag, setting an environment variable or editing a config file. Those affordances are absent from the build, not disabled within it. |
| **CS-ENV-05** | Build-time configuration is distinguished from runtime site configuration. Site-specific values — retention period, timezone, enabled detection rules — come from the API, never from the bundle. One build serves every site. |

---

## 20. Comments and documentation

| ID | Rule |
|---|---|
| **CS-M-01** | Comments explain **why**, never what. A comment restating the code is deleted. |
| **CS-M-02** | Any code implementing a business rule carries the rule ID: `// BR-V-02 — single-event disposition only.` This is how a future reader knows the constraint is deliberate rather than incidental. |
| **CS-M-03** | Non-obvious workarounds carry a JSDoc block naming the cause and the removal condition. |
| **CS-M-04** | `TODO` requires an owner and a ticket: `// TODO(GL-142, kuldeep): …`. A bare TODO fails lint. |
| **CS-M-05** | Exported hooks and utils carry a one-line JSDoc summary. Components do not need one if the name and props are clear. |
| **CS-M-06** | No commented-out code. Git remembers it. |
| **CS-M-07** | A pull request that touches a §17 or §18 rule states which rule and how it was verified. This is the trace a reviewer needs and cannot reconstruct from the diff. |

---

## 21. Mechanical enforcement

A standard that relies on human memory decays. Everything below runs in CI (TRD §19: `tsc`, `eslint`, `vitest` are already gates).

### 21.1 `tsconfig.json` — required compiler options

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,      // CS-G-14
    "exactOptionalPropertyTypes": true,    // CS-T-15
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,    // CS-T-14
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "allowUnreachableCode": false,
    "verbatimModuleSyntax": true,          // CS-C-04
    "paths": { "@/*": ["./src/*"] }        // CS-F-06
  }
}
```

### 21.2 ESLint — the rules that carry this document

| Standard | Rule |
|---|---|
| CS-T-05 (`any`, assertions, `!`) | `@typescript-eslint/no-explicit-any`, `no-unsafe-*`, `no-non-null-assertion`, `ban-ts-comment`, `no-unnecessary-type-assertion`; review the few documented interop exceptions |
| CS-T-10 | Targeted review or scoped `@typescript-eslint/explicit-module-boundary-types` for stable library/domain APIs; framework adapters may use inference |
| CS-T-14 | `@typescript-eslint/switch-exhaustiveness-check` |
| CS-C-03 | `import/no-default-export` (with config-file overrides) |
| CS-C-05 / C-07 / C-08 | Review signals supported by `sonarjs/cognitive-complexity`; line, prop and nesting counts are not pass/fail proxies for design quality |
| CS-C-11 | `react/no-array-index-key` |
| CS-C-10 | `no-nested-ternary` |
| CS-C-04 / §4.2 import order | `simple-import-sort` (or `import/order`) with the group order fixed to react → external → `@/` → relative → type-only |
| CS-F-01 / F-02 | `import/no-restricted-paths` — zone rules: `ui` may not import `features` or `types`; features may not deep-import each other |
| CS-F-04 | `import/no-cycle` |
| CS-U-06 | Scoped `react/forbid-elements` override for feature files; allow native controls only in `components/ui/**` |
| CS-D-01 | Scoped `no-restricted-globals: fetch` override; allow it only in the API transport module and test infrastructure |
| CS-S-07 | `no-restricted-imports`: `redux`, `zustand`, `mobx`, `jotai` |
| CS-ENV-01 | `no-restricted-properties` / `no-restricted-syntax` on `import.meta.env` outside `lib/env.ts` |
| CS-AU-06 / CS-AU-07 | `no-restricted-syntax` on `localStorage`/`sessionStorage` writes outside `hooks/useLocalStorage` and the session-draft hook; secret scanner covers the rest. Token storage is a review item |
| CS-PG-01 / CS-PG-05 | `no-restricted-syntax` on `offset`/`page=` request params and on numeric literals passed as `limit` outside `constants/query.ts`; cursor opacity is a review item |
| CS-SC-01 / CS-RT-01 | CI grep asserts every route in `router.tsx` has a `ROUTES` constant and a §23.1 row; a new screen fails the check until the TRD and this table are updated |
| CS-A-* | `plugin:jsx-a11y/recommended` at error |
| Hooks correctness | `react-hooks/rules-of-hooks` and `react-hooks/exhaustive-deps` at error |
| CS-M-04 | CI grep/custom lint rule validates the exact ticket-and-owner TODO format; `no-warning-comments` alone cannot do this |
| CS-Y-06 | `prettier-plugin-tailwindcss` |
| CS-P-02 | Bundle-size budget check (`size-limit` or the equivalent Vite plugin) as a CI gate |
| Security | `eslint-plugin-no-unsanitized`, restricted DOM APIs and secret/dependency scanners; security review covers rules that static analysis cannot prove |
| General | `sonarjs/no-identical-functions`, `sonarjs/cognitive-complexity`, `unicorn/no-useless-undefined` |

### 21.3 CI gate

Use package scripts as the single local/CI entry point. The required gates are `tsc --noEmit` · `eslint --max-warnings 0` · `vitest run --coverage` · `prettier --check` · production build · bundle-size budget · dependency/secret scan. **All must pass; warnings are errors.** Pin the Node and package-manager versions and use a frozen lockfile in CI.

### 21.4 Dependencies this standard implies

TRD §3 lists React, TypeScript, Vite, Tailwind and TanStack Query. The rules above additionally require the following. **They are not yet registered in the TRD and need either a Technical Decisions Register entry or an addendum before the first commit that installs them.**

| Purpose | Package | Rule |
|---|---|---|
| Wire types from OpenAPI | `openapi-typescript` | CS-T-01 |
| Runtime schemas derived from the same contract | An OpenAPI→schema generator (e.g. `orval`, `openapi-zod-client`) over hand-written Zod | CS-D-04, CS-G-10 |
| Form state | `react-hook-form` + schema resolver | CS-FM-01 |
| Routing | `react-router-dom` | §8 |
| Class composition | `clsx` + `tailwind-merge` | CS-Y-03 |
| Network mocking in tests | `msw` | CS-Q-03 |
| Accessibility assertions | `vitest-axe`, `@testing-library/*`, `@testing-library/user-event` | CS-A-09, CS-Q-01 |
| Lint plugins | `eslint-plugin-jsx-a11y`, `eslint-plugin-import`, `eslint-plugin-sonarjs`, `eslint-plugin-unicorn`, `eslint-plugin-no-unsanitized`, `eslint-plugin-simple-import-sort` | §21.2 |
| Bundle budget | `size-limit` or equivalent | CS-P-02 |

> Choosing the OpenAPI→schema generator is the one open decision in this table, and it should be made before the first API hook is written. Writing Zod by hand now and generating later means rewriting every schema and re-testing every boundary.

---

## 22. Testing

| ID | Rule | Source |
|---|---|---|
| **CS-Q-01** | Vitest + React Testing Library. Tests assert **behaviour a user can observe**, never internal state or implementation. | TRD §19.2 |
| **CS-Q-02** | Query by role and accessible name (`getByRole('button', { name: /accept/i })`). `data-testid` is a last resort and requires a comment justifying it. | — |
| **CS-Q-03** | Network is mocked with MSW against the **generated** API types, so a contract change breaks the tests. Never hand-mock the query hook itself. | — |
| **CS-Q-04** | Test data comes from typed factories in `test/factories/`. No inline object literals fabricating an `Event`. | — |
| **CS-Q-05** | Coverage: **80% overall** and **100% branch coverage on business-rule guards**, as required by TRD §19.2. Primitive tests are risk-based; do not chase line coverage with assertions that prove nothing. | TRD §19.2 |
| **CS-Q-06** | Each applicable async screen covers happy, error, empty and loading states. Every interactive flow covers keyboard operation; add boundary and permission cases based on risk. | — |
| **CS-Q-07** | The DecisionBar keyboard bindings and the StatusChip non-colour indication have dedicated named tests — the TRD calls them out explicitly. | TRD §19.2 |
| **CS-Q-08** | CI runs type-check, lint, unit/integration tests, formatting, production build and security scans using the frozen lockfile. Test failures and warnings are not waived in a feature PR. | TRD §19 |
| **CS-Q-09** | Use snapshots only for small, stable serialisations where the full output is the contract. Do not use broad component snapshots as a substitute for behavioural assertions. | — |
| **CS-Q-10** | Every §17 prohibition has a named absence test asserting the affordance and its data are not rendered — not that they are disabled. These tests are the frontend half of the RULE_BOOK §6 enforcement matrix and are never skipped or quarantined. | RULE_BOOK §6 · TRD §19.4 |
| **CS-Q-11** | The optimistic-decision path is tested for its failure case: a rejected mutation restores the queue exactly, and no verified record is shown at any point before server confirmation. Testing only the success path leaves BR-004's most likely violation untested. | BR-004 · CS-D-06 |

---

## 23. Screens, application shell, authentication and the admin area

TRD §7.1 says *which* screens exist. This section says what every one of them must look like structurally, so that twelve screens built by different agents at different times are recognisably one application: one shell, one navigation, one login, one administration area, one table, one pagination control.

### 23.1 The screen inventory is fixed

Every route in the application maps to exactly one row of TRD §7.1. **A screen that is not in this table is a TRD change, not a frontend decision.**

| ID | Screen | Route constant | Feature directory | Minimum role | Scope |
|---|---|---|---|---|---|
| SCR-1 | Login | `ROUTES.LOGIN` | `features/auth` | — (public) | `[MVP]` |
| SCR-2 | Review Queue — **home** | `ROUTES.QUEUE` | `features/review-queue` | `reviewer` | `[MVP]` |
| SCR-3 | Candidate Detail | `ROUTES.CANDIDATE` | `features/review-queue` | `reviewer` | `[MVP]` |
| SCR-4 | Event History | `ROUTES.HISTORY` | `features/event-history` | `reviewer` | `[MVP]` |
| SCR-5 | Rejection Log | `ROUTES.REJECTIONS` | `features/rejection-log` | `reviewer` | `[MVP]` |
| SCR-6 | Reports | `ROUTES.REPORTS` | `features/reports` | `safety_manager` | `[MVP]` basic |
| SCR-7 | Camera Configuration | `ROUTES.ADMIN_CAMERAS` | `features/admin/cameras` | `site_admin` | `[MVP]` minimal |
| SCR-8 | Zone & Rule Configuration | `ROUTES.ADMIN_RULES` | `features/admin/zones-rules` | `safety_manager` | `[MVP]` minimal |
| SCR-9 | Retention Settings | `ROUTES.ADMIN_RETENTION` | `features/admin/retention` | `site_admin` | `[V1]` |
| SCR-10 | Audit Log Viewer | `ROUTES.ADMIN_AUDIT` | `features/admin/audit-log` | `auditor` | `[V1]` |
| SCR-11 | User & Role Management | `ROUTES.ADMIN_USERS` | `features/admin/users` | `site_admin` | `[V1]` |
| SCR-12 | System Health | `ROUTES.ADMIN_HEALTH` | `features/admin/system-health` | `site_admin` | `[V1]` |

| ID | Rule |
|---|---|
| **CS-SC-01** | Every screen is reachable by a typed route constant (CS-RT-01), lazily loaded (CS-RT-04) except the queue, and sits inside an error boundary (CS-RT-05). |
| **CS-SC-02** | Every screen renders inside `AppShell` (§23.2). Login, not-found and the root error screen are the only exceptions, and they render no navigation at all. |
| **CS-SC-03** | Every screen with server data renders four distinct states — loading, error, empty, content (CS-D-07) — plus end-of-list where it pages (CS-PG-13). A screen with three of the five is not finished. |
| **CS-SC-04** | Every screen sets the document title and moves focus to its `<h1>` on navigation (CS-RT-07), and has exactly one `<h1>`, rendered by `PageHeader`. |
| **CS-SC-05** | The minimum role above shapes navigation only. The API decides (CS-SEC-03, CS-RT-06), and a `403` renders an explicit "you do not have access to this" screen with a route back to the queue — never a blank page and never a silent redirect loop. |
| **CS-SC-06** | `[V1]` screens are absent until built: no route, no nav entry. A nav item that leads to "coming soon" trains users to distrust the navigation. |

### 23.2 The application shell

```
┌───────────────────────────────────────────────────────────────────────────┐
│ [skip to main]                                                            │
│ ┌── header ───────────────────────────────────────────────────────────┐   │
│ │ Guardian Lens   Site: Bay Plant ▾        340 awaiting review   A. Reviewer ▾ │
│ └─────────────────────────────────────────────────────────────────────┘   │
│ ┌── nav ─────────────┐ ┌── main ─────────────────────────────────────┐    │
│ │ REVIEW             │ │ ┌ PageHeader ─────────────────────────────┐ │    │
│ │  • Review queue 340│ │ │ H1 Event history          [ actions ]   │ │    │
│ │ RECORDS            │ │ └─────────────────────────────────────────┘ │    │
│ │  • Event history   │ │  filters (URL-backed)                       │    │
│ │  • Rejection log   │ │  ┌ Table ────────────────────────────────┐  │    │
│ │  • Reports         │ │  └───────────────────────────────────────┘  │    │
│ │ ADMINISTRATION     │ │  ┌ Pagination — Prev / Next, cursor-based ┐  │    │
│ │  • Cameras         │ │  └───────────────────────────────────────┘  │    │
│ │  • Zones & rules   │ │                                             │    │
│ │  • Users …         │ │                                             │    │
│ └────────────────────┘ └─────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────────┘
```

| ID | Rule |
|---|---|
| **CS-SH-01** | One shell: `components/layout/AppShell` composes `Header`, `SideNav` and `<main>`. A screen renders page content only — it never renders its own header, navigation or shell chrome. |
| **CS-SH-02** | Navigation items are declared once in `constants/navigation.ts`, typed against route constants and roles, grouped **Review · Records · Administration**. No component inlines a nav list or a role string. |
| **CS-SH-03** | **Queue depth is rendered by the shell, so it is visible from every screen** — not only from the queue. A backlog that disappears when the reviewer opens a report is a hidden backlog (DP-4, CS-B-08). |
| **CS-SH-04** | The shell is responsive: a persistent sidebar at `lg` and above, a drawer below it that traps focus, closes on `Escape` and closes on navigation (CS-A-05). Collapsing the sidebar never collapses the depth indicator — it moves to the header, it does not vanish. |
| **CS-SH-05** | `PageHeader` owns the `<h1>`, the optional description and the screen's primary actions; the document title derives from the same value so the tab and the heading can never disagree. |
| **CS-SH-06** | Landmarks are structural and singular: one `<header>`, one `<nav aria-label="Primary">`, one `<main id="main">`, skip link first in tab order (CS-A-10). |
| **CS-SH-07** | The toast region and the `aria-live` announcer are mounted once, by the shell. A feature that mounts its own announcer produces double announcements. |
| **CS-SH-08** | Nothing in the shell interrupts the review path: no onboarding interstitial, no marketing modal, no notification pane covering the queue. The queue is home (TRD §7.2) and it opens ready to work. |
| **CS-SH-09** | The header states the current principal and the current site, and offers sign-out. A reviewer whose name will appear on every record they verify (BR-005) must be able to see, at a glance, whose session they are working in. |

### 23.3 SCR-1 — the login screen

Login is a two-panel screen on `md` and above: **identity on the left, the form on the right.** The left panel says what the product is and what the person is signing in to; the right panel does exactly one thing. Below `md` the panel collapses to a compact header and the form takes the full width — the fields are never pushed below the fold on a phone.

```
┌────────────────────────────────┬──────────────────────────────────┐
│  Guardian Lens                 │   H1  Sign in                    │
│                                │                                  │
│  Human-verified safety and     │   Email                          │
│  compliance monitoring for     │   [                          ]   │
│  the cameras you already own.  │                                  │
│                                │   Password                       │
│  • Nothing is recorded until   │   [                      ] [👁]   │
│    a person confirms it.       │                                  │
│  • Nothing outside a           │   [ Sign in                  ]   │
│    configured safety rule is   │                                  │
│    watched at all.             │   ⚠ Email or password is         │
│                                │      incorrect.                  │
│  (decorative, alt="")          │                                  │
└────────────────────────────────┴──────────────────────────────────┘
   ≥ md: 2 columns          < md: panel collapses to a header, form full width
```

| ID | Rule |
|---|---|
| **CS-AU-01** | Login renders outside `AppShell` and contains **no navigation** — no sidebar, no site switcher, no links into the application. There is nothing to navigate to yet. |
| **CS-AU-02** | The left panel is informational and decorative only. It carries no controls, no second form, and **no imagery of workers and no evidence frame** — an evidence frame on an unauthenticated screen is a retention and privacy breach (BR-006, CS-SEC-10). Decorative images carry `alt=""` (CS-A-07). |
| **CS-AU-03** | The form is one `<form>` with real `<label>`s, `autoComplete="username"` and `autoComplete="current-password"`, a `type="submit"` button — the `Button` primitive defaults to `type="button"` (§5.2), so submit must be passed explicitly — and Enter submits from either field. |
| **CS-AU-04** | **A `401` renders one generic message: "Email or password is incorrect."** The UI never distinguishes an unknown account from a wrong password, never reveals whether an email exists, and never varies its wording or timing by cause — TRD §10.2 requires no user enumeration. It renders as persistent form-level text with `role="alert"`, not a toast that vanishes before it is read. |
| **CS-AU-05** | A `429` (TRD §12.7: 5/min per IP, 10/hour per account) renders an honest, distinct message stating that too many attempts have been made and when to try again. The client never auto-retries a login and never silently swallows the limit into the generic credential error. |
| **CS-AU-06** | Submit is disabled **only while the request is in flight** (CS-FM-05). The password is never logged, never written to `localStorage` or `sessionStorage`, never placed in a query string, and never included in an error report (CS-SEC-04). |
| **CS-AU-07** | The access token is held **in memory only**; the refresh credential follows CS-SEC-06. Tokens never go to `localStorage`. Refresh is single-flight and centralised in the API client (CS-D-13) — no component refreshes a session. |
| **CS-AU-08** | On success, redirect to the route the user was trying to reach, captured as an internal path before the redirect to login and **validated as a same-origin relative path** (CS-SEC-05) — an open redirect on the login screen is a credential-phishing surface. With no captured intent, the destination is the review queue. |
| **CS-AU-09** | On a `401` from any request, the API client clears the principal, clears the query cache and routes to login preserving intent. On sign-out it clears the cache, `sessionStorage` drafts and any cached evidence URL (CS-SEC-07). A stale queue must never be visible after sign-out. |
| **CS-AU-10** | **v1 has no self-service registration, no email password reset, no social sign-in and no "forgot password" flow.** Users are created by a `site_admin` (TRD §10.6). These affordances are absent from the build, not hidden — anything else is an account-enumeration surface the API does not back. |
| **CS-AU-11** | Login is fully keyboard-operable, focuses the email field on mount, moves focus to the error on a failed submit (CS-FM-04), keeps visible focus rings (CS-Y-08) and remains usable at 200% zoom. It is the first screen every user meets; it is not exempt from §15. |

### 23.4 Roles and navigation

Four roles (TRD §12.3). The frontend uses them to decide what to *show*; the server decides what is *allowed* (CS-SEC-03).

| Role | Sees in navigation |
|---|---|
| `reviewer` | Review queue, candidate detail, event history, rejection log |
| `safety_manager` | The above + reports + zones & rules |
| `site_admin` | Everything, including cameras, users, retention, system health |
| `auditor` | Event history, rejection log, audit log — **read-only: no decision affordance is rendered at all** |

| ID | Rule |
|---|---|
| **CS-RB-01** | The role→navigation mapping is declared once (CS-SH-02). A component that writes `role === 'site_admin'` inline is a duplicate of that mapping and will drift from it. |
| **CS-RB-02** | Role checks shape navigation and rendering only. Every screen still handles `403` (CS-SC-05), because a role in a token is a claim, not an authorisation. |
| **CS-RB-03** | For a role that cannot act, the action is **absent, not disabled**. An auditor sees a record; they do not see a greyed-out Accept button implying a decision they might have made. |
| **CS-RB-04** | No role, flag or configuration makes a §17 prohibition reachable. `site_admin` is not a bypass — there is no role in this product that can bulk-accept, view a person, or auto-dispose, because those affordances do not exist for anyone (CS-ENV-04). |

### 23.5 The admin area (SCR-7 … SCR-12)

The admin area is where a site expands what is watched. Every screen in it changes the product's scope over real people, so its rules are stricter than its visual importance suggests.

| ID | Rule |
|---|---|
| **CS-AD-01** | Admin screens use the **same shell, same primitives, same tokens** as the review screens. There is no second design system for administration and no second Button (CS-U-01). |
| **CS-AD-02** | Admin routes nest under `/admin` inside `AdminLayout`, which adds a breadcrumb and the section's secondary navigation. Every admin list is `Table` + `Pagination` per §9.5; every admin form obeys §10. |
| **CS-AD-03** | **Enabling monitoring is an explicit, confirmed submit — never a toggle that acts on flip.** Activating a rule, adding a camera, changing a zone, altering retention or deactivating a user requires a confirmation step that names in plain words what will change and where. BR-001 (nothing monitored by default) and BR-C-02 (activation is always explicit) are enforced here or nowhere. |
| **CS-AD-04** | Scope-changing submits are **never optimistic** (CS-D-06). The UI shows the new state only after the server confirms it, because the configuration change and its audit entry are written in one transaction (BR-C-01) — a change that was not audited did not happen, and must not appear to have. |
| **CS-AD-05** | The rule configuration form carries the written site safety rule reference (BR-011). Its absence renders a visible, non-blocking warning — advisory means flagged, not prevented. |
| **CS-AD-06** | **Camera credentials are write-only.** The stream URL and credentials are entered, submitted and thereafter shown masked with a "replace" action. The UI never requests, renders, logs or round-trips a stored credential (BR-S-03, NFR-SEC-02). Use "test connection" (TRD §10.6) for feedback, never credential echo. |
| **CS-AD-07** | The retention screen states the effect in plain language before submit: what will be deleted, when, and that deletion is permanent and audited (BR-009, EP-6). A retention period is not a number in a box; it is an instruction to destroy evidence on a schedule. |
| **CS-AD-08** | User management renders identity, role and scope only. **No worker exists in this product and no user-activity surface is built**: no login counts, no decisions-per-hour, no reviewer leaderboard, no productivity chart (BR-002, CS-B-02). Reviewer identity is never a client-supplied field anywhere (BR-S-01, CS-B-05). |
| **CS-AD-09** | The audit log viewer is read-only: no edit, no delete, no bulk action. Filters narrow the view, and the applied filter is always stated alongside a one-click clear, so a filtered log is never mistaken for the whole log (NFR-AUD-02). |
| **CS-AD-10** | System health never implies a false all-clear. Unknown, stale and unreachable are distinct rendered states — text plus icon, never colour alone (CS-A-02) — and a missing heartbeat renders as *unknown*, not *healthy*. Coverage gaps are shown as recorded gaps (FR-005, PR-6). |
| **CS-AD-11** | Every admin screen is code-split and stays out of the queue's critical bundle (CS-RT-04, CS-P-02). Administration is occasional; the queue is the daily job. |
| **CS-AD-12** | Admin screens carry the same accessibility obligations as the review path: keyboard-operable throughout, labelled fields, associated errors, focus management on submit (§15). "It is only used by an administrator" is not an exemption. |

### 23.6 Screen-level tests this section requires

| Test | Asserts |
|---|---|
| Login — invalid credentials | One generic message; no wording, timing or field-level hint that distinguishes unknown account from wrong password (CS-AU-04) |
| Login — rate limited | Distinct `429` message; no automatic retry (CS-AU-05) |
| Login — redirect intent | A captured internal path is honoured; an absolute or cross-origin `next` is rejected and the queue is used (CS-AU-08) |
| Sign-out | Query cache and session drafts cleared; protected content unrenderable afterwards (CS-AU-09) |
| Shell — depth visibility | Queue depth is present on a non-queue screen and at mobile width (CS-SH-03, CS-SH-04) |
| Navigation by role | An `auditor` session renders no decision affordance anywhere — absent, not disabled (CS-RB-03) |
| Pagination — filter change | Changing a filter clears the cursor from the URL and refetches page one (CS-PG-06) |
| Pagination — keyboard and announcement | Next/Previous operable by keyboard; the current range is announced (CS-PG-14) |
| Pagination — depth | The depth badge reflects the server total, not the page length (CS-PG-08) |
| Admin — activation | A rule becomes active only after an explicit confirmed submit and a server-confirmed response (CS-AD-03, CS-AD-04) |
| Admin — credentials | No stored camera credential is ever rendered or returned into a form field (CS-AD-06) |

---

## 24. Definition of Done

A change is not done until every line is true. This is the review checklist; use it verbatim.

- [ ] Generated and existing domain contracts were reused; new types are owned at the narrowest sensible scope
- [ ] No unexplained `any`, assertion, non-null assertion or TypeScript suppression
- [ ] Existing primitives, feature code, hooks and utilities were searched before adding a new concept
- [ ] Any new abstraction represents shared meaning and has a coherent API
- [ ] Components have named exports, focused responsibilities and reviewable JSX
- [ ] Orchestration, presentation and domain transformations are separated where non-trivial
- [ ] External values are validated once at the boundary; internal code trusts the validated contract
- [ ] All server state via TanStack Query, with a key factory; mutations invalidate precisely
- [ ] Filters, sort, pagination and selection are held in the URL, not component state
- [ ] Lists page through the server cursor contract; the cursor resets on any filter change; depth is the server total
- [ ] The screen renders inside the shell, sets its title, owns one `<h1>` and moves focus on navigation
- [ ] Loading, error, empty, end-of-list and `403` are distinct rendered states
- [ ] Forms validate through one schema, associate errors with fields, and never discard user input on failure
- [ ] Timestamps and confidence render through the shared formatters, with zone and unit shown
- [ ] Policy values, routes, storage keys and non-obvious literals are named; trivial literals remain local
- [ ] Keyboard-operable; no colour-only status; passes `jsx-a11y` and `vitest-axe`
- [ ] Performance claims are backed by a recorded measurement; the bundle budget still passes
- [ ] Nothing forbidden by §17 was built; UI, API or compile-time absence is tested at the correct layer
- [ ] No secrets or sensitive payloads are exposed, persisted or logged; auth failures are handled centrally (§18)
- [ ] No new configuration or flag makes a §17 prohibition reachable
- [ ] Vocabulary matches RULE_BOOK §3.1 — in code and in user-facing copy
- [ ] Business-rule code cites its rule ID in a comment
- [ ] Tests cover applicable happy, error, empty, loading, keyboard, permission and boundary paths
- [ ] Type-check, lint, tests, format check, production build and security scans all pass with the frozen lockfile

---

## 25. Precedence and change control

1. Where this document conflicts with the **RULE_BOOK**, the Rule Book prevails, always and without exception.
2. Where it conflicts with the **TRD** on architecture or stack, the TRD prevails; this document is corrected.
3. Where it conflicts with a supported library's documented correctness, security or accessibility guidance, stop and reconcile the conflict. Record a standard change or ADR; do not silently prefer local convention.
4. Style consistency may override an equally safe local preference, but never a correctness, security, accessibility or product requirement.
5. A justified one-off exception may be approved in review when changing the global rule would be misleading. It must name the rule ID, rationale, owner, issue and removal condition. Repeated exceptions trigger an amendment to this document.

---

## 26. Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.3 | 12 Aug 2026 | Added pagination (§9.5) — cursor-based per TRD §10.1, URL-held, opaque cursor, cursor reset on filter change, server-provided depth, explicit Next/Previous, one `Pagination` primitive. Added §23: the fixed screen inventory mapped to routes, features and roles; the application shell with always-visible queue depth; the two-panel login screen with generic `401` copy, rate-limit handling, validated redirect intent and no self-service account flows; role-shaped navigation with absent-not-disabled affordances; and the admin area rules for explicit rule activation, non-optimistic scope changes, write-only camera credentials, plain-language retention, no user-activity surfaces, read-only audit and honest health states. Extended the project structure and primitive roadmap; added screen-level tests and Definition-of-Done items. Renumbered §23–§26 to §24–§27. | — |
| 1.2 | 8 Aug 2026 | Added routing and URL state (§8), forms and user input (§10), display formatting and time (§13), performance and payload (§16), environment and configuration (§19). Extended accessibility with landmarks, shortcut scoping, reduced motion and a manual keyboard gate; added absence-test and optimistic-failure-path testing rules; added the implied-dependency register (§21.4) and import-order, cycle, env and bundle-budget lint ownership. Narrowed the optimistic-update scope against BR-004 and extended §17 with BR-R-03 visibility. | — |
| 1.1 | 8 Aug 2026 | Replaced arbitrary structural limits with review signals; clarified contract ownership, safe type exceptions and abstraction policy; corrected optimistic rollback and button loading examples; added frontend security/privacy, accurate lint ownership, production-build and supply-chain gates; aligned testing with TRD §19. | — |
| 1.0 | 8 Aug 2026 | Initial standard. Structure, types-first workflow, primitives layer, reuse policy, defensive-check policy, Rule Book enforcement in UI, mechanical enforcement config. | — |

---

## 27. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Product Owner | Kuldeep | The standard serves the product's constraints, not the other way round | |
| Engineering / Integration | Kapil | Every rule is implementable and mechanically enforceable as stated | |
| AI Engineering | Kamal | Rule Book constraints in §17 are correctly and completely reflected | |
| Test / Verification | Yashpal | Every §17 rule is verified at the correct UI, API, schema or compile-time layer; coverage targets are achievable | |
| Validation / Software | Mayank | Vocabulary in §14 matches the Rule Book exactly | |

> **The test for this document:** hand it to an agent with a feature ticket and no other context. The code it produces should be indistinguishable in shape from code written by anyone else on the team. If it is not, the standard is under-specified — not the agent.
