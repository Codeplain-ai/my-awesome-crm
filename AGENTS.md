# my-awesome-crm — project memory

A Python 3.12 / FastAPI CRM host (`src/`) with an **embedded ***plain integration project** under
`plain/`. Each of the 10 providers is one root `.plain` module (`salesforce.plain`, `dynamics.plain`, …) that imports `crm_common` + `integration_testing` and emits a
runtime-discovered plug-in at `src/integrations/<name>/` exposing a top-level `fetch(get_stored)`
callable, which returns a list of `{data_type, data}` records that the host's generic record store
persists verbatim.

## The reference and host context are auto-loaded into context

The bulk authoring context is loaded **uncapped via CLAUDE.md `@imports`** (see *Auto-loaded startup
context* at the end of this file): the full ***plain language reference, the `salesforce.plain`
structural exemplar, the `crm_common` + `integration_testing` templates, the host's `schemas.py` /
`ingest.py` / `requirements.txt`, `plain/config.yaml`, and the salesforce `openapi.yaml` +
`contact-mapping.md`. The imports expand the **live** files every session, so they never drift.

A small `SessionStart` hook (`.claude/hooks/load-integration-context.sh`) adds only the **dynamic**
piece the imports can't express: the current list of existing integrations, so you don't duplicate a
provider. (History: the hook used to dump everything, but Claude Code caps each hook output at
~10K chars and persists the overflow to a file instead of injecting it — so the heavy, static content
moved to `@imports`, which are uncapped.)

Because of this, **do not invoke `/load-plain-reference`** and **do not perform manual host discovery**
(reading those exemplar/template/host files to learn the stack) — that context is already in your
window. Host facts remain deductions, not questions. The provider-specific live-API cross-check
(`integrations.md` § *Live API must be cross-checked*) is **not** covered by this and still must be
done per integration.

## Skills to refrain from using

Do **not** invoke any of the following skills in this project:

- `/forge-plain`
- `/add-feature`
- `/add-functional-spec`
- `/analyze-if-func-spec-too-complex`
- `/analyze-2-func-specs`
- `/add-test-requirement`
- `/add-test-requirement`
- `/add-functional-specs`
- `/add-test-requirement`
- `/add-implementation-requirement`
- `/add-concept`

**When building a new integration, always run `/plain-healthcheck` at the end.**

## Never spawn agents or workflows in this repo

**Agents and workflows should never be spawned in this repo.** Do not use the `Agent` tool (of any
`subagent_type`, including `fork`, `Explore`, `Plan`, and `general-purpose`) and do not use the
`Workflow` tool. All work — authoring, editing, reviewing, debugging, host discovery, and API
cross-checks — is done directly in the main conversation. The full authoring context is already
loaded via CLAUDE.md `@imports`, so there is no research a subagent could do that this session
cannot do itself.

## Do not create a plan when writing plain specs

When authoring, editing, reviewing, or debugging any `.plain` content, **do not use the plan tool**
and do not produce a written plan. Spec authoring is governed end-to-end by the rules in
`.claude/rules/` and the lessons in this file — that workflow is the plan. Work the rules directly
instead of drafting a separate one.

## First step: create the empty `.plain` module with its frontmatter

When a user asks to create a new integration, the **very first action** — before any questions, host
discovery narration, or resource authoring — is to create the empty root `.plain` module at
`plain/<provider>.plain` containing **only** the YAML frontmatter (no spec sections yet). Mirror the
salesforce frontmatter exactly. Template:

```yaml
---
import:
  - crm_common
  - integration_testing
description: "<Provider> Integration plug-in for the CRM backend."
---
```

## Ask the user at least 3-5 questions, one at a time — and write a spec after every answer

When building a new integration, **always ask the user at least 3-5 questions**. Ask them **one by one** — never batch them into a single multi-question prompt — so each
answer can inform the next question. Focus the questions on what the codebase cannot tell you: the
provider and its API, authentication and credentials, and edge cases (pagination, empty/dirty
records, boundary shapes). Everything the host already encodes is a deduction, not a question
(`integration-embedded.md` § *Discover before you ask*).

**After every answer, fold it into the `.plain` module (and its linked resources) BEFORE asking
the next question.** This is a hard rule inside the question loop, not a drafting phase you defer
until the interview is over. The loop is: *ask one question → user answers → write the spec → ask
the next question.* Each write must follow the **spec-writing style of `salesforce.plain`** (the
structural exemplar) exactly:

- Put the answer where it belongs. The module has only two authored sections: `***definitions***`
  for a concept and `***functional specs***` for a functionality. Everything structural about the
  provider's API goes in the linked resources — the OpenAPI file (`resources/<provider>/openapi.yaml`)
  and the mapping doc (`resources/<provider>/contact-mapping.md`). The module authors **no**
  `***test reqs***` and **no** `***implementation reqs***`.
- Mirror salesforce's shape: **3 definitions and 3 functional specs, and nothing else.** The whole
  API surface lives behind `:<Provider>RestAPI:` in `resources/<provider>/openapi.yaml` and the
  mapping contract behind `:<Provider>ContactMapping:` in `resources/<provider>/contact-mapping.md`
  (see *Authoring the next integration* below).
- Inherit **all** shared reqs silently from `crm_common` (implementation reqs, tech stack,
  skip-and-log policy, layout/identifier contract, the `:UnitTests:` policy) and `integration_testing`
  (the entire `:ConformanceTests:` policy, including the pure-function `:Mapping:` check) — never
  restate any of them.


## North star: render green on the FIRST `codeplain` run

The goal for every new integration is a clean render with **no mid-render stop-edit-rerender**. A
mid-render stop to edit specs is a **red flag**: a gap that should have been closed during authoring
leaked into the render. The whole rule set is built to make that gap impossible — live-API
cross-checks surface surprises before authoring (`integrations.md` § *Live API must be
cross-checked*), the mapping contract and the OpenAPI record schema are pinned so the pure-function
conformance check can exercise the mapping against generated records, and all cross-cutting behavior
already lives in the inherited `crm_common` / `integration_testing` reqs so it is in scope from
functionality 1 (`impl-reqs.md` § *Encapsulation warning*).

When a mid-render stop happens anyway, do not just patch and move on — **fold the fix back into the
specs AND into this file** so the next integration never hits it.

## Authoring the next integration — `salesforce.plain` is the structural exemplar

**Read `plain/salesforce.plain` before authoring — it is the source of truth for the shape, not this
description.** The per-provider module is deliberately tiny: **3 definitions and 3 functional specs,
and nothing else.** It authors **no `***implementation reqs***` and no `***test reqs***`** — every
cross-cutting requirement is inherited silently from `crm_common` (tech stack, skip-and-log policy,
layout/identifier contract, the `:UnitTests:` policy, the host ground-truth links) and
`integration_testing` (the entire `:ConformanceTests:` policy, including the pure-function
`:Mapping:` check and the live `fetch` check).

- **3 definitions** (each one line, mirroring salesforce):
  - `:<Provider>Integration:` — "is an `:Integration:` for the `<Provider>` `:Provider:` with identifier `<id>`." The provider identifier lives inline here; there is **no** separate provider-id concept.
  - `:<Provider>RestAPI:` — "is the exact `<Provider>` REST API surface this integration calls, defined by [resources/<provider>/openapi.yaml](...)." The **only** link to the OpenAPI file.
  - `:<Provider>ContactMapping:` — "is a `:Mapping:` for `:<Provider>Integration:`, fully described in [resources/<provider>/contact-mapping.md](...)." The **only** link to the mapping doc.
  - There is **no** standalone credentials concept — the env-var names are named inline in the `fetch` functional spec, and `:IntegrationCredentials:` is inherited from `integration_testing`.
- **0 test reqs and 0 implementation reqs in the module.** The pure-function `:Mapping:` conformance
  check, the live `fetch` conformance check, the `:UnitTests:` policy, and the tech stack are all
  inherited — never restate any of them.
- **3 functional specs** (each a single top-level bullet, mirroring salesforce):
  1. "`:<Provider>ContactMapping:` maps one `ContactRecord` of `:<Provider>RestAPI:` to a `:Contact:`." — one line, **no** sub-bullets; the field-by-field contract lives entirely in the mapping doc.
  2. "`:<Provider>Integration:` exposes a `fetch(get_stored)` entry point." — with sub-bullets that name the required environment variables, state it "raises `RuntimeError` naming any environment variable key that is missing or empty", and say it "follows `:<Provider>RestAPI:` to authenticate, read every page of contacts, map every record with `:<Provider>ContactMapping:`, and return the mapped `:Contact:` data dicts."
  3. "`:<Provider>Integration:` exports `fetch_contacts()` from `__init__.py`." — the host plug-in contract (the top-level `fetch(get_stored)` callable) comes from `crm_common`; this spec adds only the provider's exported entry point. There is no `DATA_TYPE` attribute — each record carries its own `data_type`.

### The whole API surface lives in `resources/<provider>/openapi.yaml`, reached through one concept

Author the OpenAPI file **first**, from the live cross-check, and put **everything** in it: the auth
/ token endpoint with its request body, the query endpoint with the pinned query string as a schema
`const`, required headers, the API-version pin **with the reason**, the pagination envelope and its
mechanics, the record schema (with dirty-data annotations like "Email is NOT guaranteed valid"), the
error envelope, and every docs-vs-live discrepancy ("live API wins"). Define `:<Provider>RestAPI:`
in `***definitions***` carrying the **only** link to
the file; spec text then says "the token endpoint / query endpoint / pagination envelope of
`:<Provider>RestAPI:`" and **never** restates URLs, headers, fields, status codes, or continuation
markers (`nextRecordsUrl`, `@odata.nextLink`) inline. The pagination spec line is one sentence —
the exemplar's reads "Read every subsequent page per the pagination envelope of
:SalesforceRestAPI: until all pages are read." This per-provider folder layout deliberately
supersedes the flat `resources/<provider>.openapi.yaml` path in `integrations.md`'s artifact table
for this project; follow the folder layout.

### The mapping contract lives in `resources/<provider>/contact-mapping.md`, reached through one concept

The full field-by-field contract — mapping table, `full_name` derivation cascade, `primary_email`
handling (lowercased and trimmed, `None` when missing or empty; **no** validation and **no**
record-skip, because the host stores the `data` verbatim), `custom_fields` rules, and the error
contract (the mapping is **best-effort and never raises** for record content — an absent value
becomes `None`, an underivable `full_name` becomes an empty string) — lives in the mapping doc,
attached to a `:<Provider>ContactMapping:` concept. Functional spec 1 is then a **single line** —
"`:<Provider>ContactMapping:` maps one `ContactRecord` of `:<Provider>RestAPI:` to a `:Contact:`." —
with **no** sub-bullets. The input shape (one `ContactRecord` of `:<Provider>RestAPI:`), the output
(the `:Contact:` data shape), the `provider_id` literal, and every field rule all live in the
mapping doc, not in the spec. **No function name, no file path, no deferral bullets.**

### `crm_common` owns the cross-cutting reqs — author only the per-provider residue

`template/crm_common.plain` now carries (a new integration must **not** restate any of it):

- the **skip-and-log batch policy** (generic, "provider-side id" abstracted) — a dormant safety net:
  if a per-record mapping raises `ValueError` the record is skipped and logged, but the mappings are
  written best-effort and never raise, so in practice it does not trigger,
- the **layout/identifier contract**: the only file contract is `src/integrations/<id>/__init__.py`
  exposing a top-level `fetch(get_stored)` callable that returns a **list** of records, each a dict
  with a `data_type` string and a `data` object; the host stores each `data` object verbatim as a
  `:Record:` row (no host-side validation, dedup, or merge); internal organization is explicitly
  optional. There is **no** `DATA_TYPE` module attribute in the contract — each record carries its
  own `data_type`,
- the **integration `:UnitTests:` policy** (no network, single indirection seams, inline dict
  payloads, and the two mandatory coverage cases: the `fetch(get_stored)` entry point returns the
  mapped records tagged with their `data_type` + `data`, and multi-page pagination),
- the **host ground-truth links**, linked once and in place: `../src/services/ingest.py` (on the
  `:Integration:` concept — discovery + invocation logic) and `../requirements.txt` (under the pip
  req — the no-re-pin source of truth). Never re-link or paraphrase these per-module.

The exemplar's `fetch` spec keeps to that functionality's WHAT — authenticate, read every page, map
every record, return the mapped dicts — and does **not** restate the shared skip-and-log policy (that
lives once in `crm_common`). A functional spec may narrate per-record behavior only when it *is* that
functionality's WHAT; the prohibition is on restating a shared `crm_common` policy as a second
requirement in the module.

### Never mandate internals — and know what the relaxation costs

Do not pin internal file names (`client.py`, `mapping.py`), private function names
(`_acquire_token`, `_get_json`), or per-file re-export wording. The contract is behavior plus the
`__init__.py` exports — the top-level `fetch(get_stored)` callable (from `crm_common`) and the
provider's exported entry point (`fetch_contacts()` in the exemplar). Evidence this is real: after the mandates were removed, the re-render
**deleted `client.py`** and folded the client logic into `__init__.py` — correct per the contract.
Two costs to watch:

- the previously mandated injectable seams went away with the file mandates. If a render produces
  hard-to-mock code, tighten `crm_common`'s *behavioral* seam req ("single indirection seams"),
  not the per-module spec;
- **pins hide in linked resources.** The mapping doc's preamble still pinned the function name and
  `mapping.py` after the spec text was cleaned, and the renderer obeyed the doc (that's why
  `mapping.py` survived the re-render). Linked resource docs must obey the no-internals rule too —
  sweep them when stripping mandates from spec text.

### Error-message specs must name the identifier space (render incident, 2026-06-12)

The renderer flagged a **Specification ambiguity** on "raise a `RuntimeError` naming the missing
variable": "variable" could mean an internal dict key (`endpoint`) or the env-var key
(`SALESFORCE_ENDPOINT`), and the conformance test asserts the **literal string**. Rule: when a spec
mandates that an error message "names" something, pin the identifier space and give an example —
"naming the missing environment variable key (e.g. `SALESFORCE_ENDPOINT`)". The fix is folded into
`salesforce.plain`; phrase it that way from the start in every new integration.

### Pre-launch and post-render checks this session added

- **Verify `.env` keys literally match the spec'd env-var names.** A `SALESFORCE_SLIENT_SECRET` typo
  (for `SALESFORCE_CLIENT_SECRET`) is caught by neither the pure-function conformance test nor the
  unit tests; it only surfaces when the integration actually runs against the provider (a
  `RuntimeError` naming the missing variable). Check the names by eye against the credentials concept.
- **Always check the `.env` file at the repo root first when looking for credentials to do the
  live-API cross-check probing (`integrations.md` § *Live API must be cross-checked*).** It already
  carries credentials for several providers (e.g. Salesforce, Dynamics) under the exact env-var
  names the runtime and conformance tests read. Only ask the user for credentials when the provider
  being probed has no entry there yet. Never print or paste the values themselves into a spec,
  summary, or commit — reference them by env-var name only.
- **Keep `verbose: true` in `plain/config.yaml`.** codeplain's `--verbose` defaults to *disabled*;
  without the config pin the log carries no test-script output, which silently blinds both the
  post-render mining below and `run-codeplain`'s spec-deviation classification.
- **After every render, mine `conformance_tests/<module>/.memory/conformance_test_memory/*.json`**
  and the log for `Specification ambiguity detected` blocks. Every RESOLVED entry and ambiguity
  suggestion is a render-time incident whose lesson gets folded into the specs and this file.

## Conformance is a pure-function mapping check — and specs still render incrementally

The renderer builds functional specs **one at a time, top to bottom**, and it cannot see specs that
render later (`func-specs.md`: no knowledge of future specs). The `:<Provider>ContactMapping:`
conformance test is a **pure-function check**: it generates dummy provider records from the
`ContactRecord` schema of `:<Provider>RestAPI:` and maps each one directly — it does **not** call the
live API or `fetch(get_stored)`. So the mapping contract and the OpenAPI record schema must be
complete and mutually consistent before the mapping functionality renders.

**Consequence:** any cross-cutting runtime behavior (tech stack, the credential-read policy, the
skip-and-log seam, the `:UnitTests:` policy) is already carried by `crm_common` / `integration_testing`
and is in scope for **all** functionalities — the module does **not** author it, and it must never be
tucked into a later functional spec. Provider-specific mechanics (the pagination envelope, the record
schema, the pinned query) live in the OpenAPI resource, not in a spec or an impl req. A per-provider
functional spec carries only that functionality's WHAT.

## Live data is dirty — the mapping absorbs it best-effort, the host stores it verbatim

Live orgs contain malformed and half-empty records: missing names, absent emails, null lookups, odd
types. The mapping absorbs all of it **best-effort** — an absent value becomes `None`, an underivable
`full_name` becomes an empty string — and **never raises** for record content. The host then stores
whatever the mapping emits **verbatim** (no required fields, no validation, no dedup, no merge), so a
dirty record is stored as-is rather than dropped. Nothing is silently lost, and a sync of N provider
records yields N stored rows.

The live-API cross-check still matters: probe for the boundary shapes (empty list, null fields,
missing lookups, multi-page) so the mapping's `None`/empty-string fallbacks and the OpenAPI record
schema's dirty-data annotations ("Email is NOT guaranteed valid") are grounded in what the provider
actually returns, not guessed. Record those boundary findings in the OpenAPI file's field
descriptions.

## Pin the third-party SDK API surface — not just the provider's REST API

`integrations.md` § *Live API must be cross-checked* requires fetching and grounding the provider's
REST docs. That is not enough when the integration depends on a **client library**: the renderer will
otherwise guess constructor kwargs and method names and get them wrong.

**Rule:** for any SDK the integration depends on, fetch the library's own docs and save the snapshot
**alongside the provider docs** under `plain/resources/docs/<provider>/` (these are saved copies; host
source files are instead linked in place per `integration-embedded.md` § *Link host files at their
original path*). Note the practical reality under the current template: `crm_common` forbids adding
any package, so an integration may depend on an SDK **only** if that SDK is already in the host
manifest — and a standard contact integration uses the host's `httpx`, no SDK at all (salesforce
forbids any Salesforce SDK). If an SDK genuinely is in the host manifest and its API surface must be
pinned (constructor kwargs, method names, token calls), that pin is a **shared** requirement and
belongs in `crm_common` (or a dedicated import module) — **not** in a per-provider module, which
authors no `***implementation reqs***`. Raise it with the user as a host-manifest decision.

## Declare which dependencies are already available in the system — don't assume

The host environment (`requirements.txt`) is the **only** set of packages the rendered integration
can rely on. The renderer cannot see what is installed; if the specs don't say it, it will guess —
and a guess that names an absent package, or re-adds one the host already ships, surfaces only at
runtime (import error) or as an avoidable second pin. `integration-embedded.md` § *The host codebase
dictates the tech stack* makes the host manifest ground truth, and § *Discover before you ask*
requires reading it **before** the first authoring question; this lesson makes the result explicit in
the spec.

**Rule:** as part of host discovery, enumerate the dependencies already available in the system from
`requirements.txt`. Under the current template the per-provider module authors **no**
`***implementation reqs***`, so this is a *constraint you honor while authoring*, not something you
restate in the module:

- The host packages the integration **reuses as-is** (e.g. `httpx`, `requests`, `pydantic`) are
  already pinned by the host and constrained by `crm_common` ("every `:Integration:` must use only the
  packages already available in the host manifest"). Do **not** re-pin or re-add them, and do **not**
  restate this per module (`integration-embedded.md` § *No host-overlapping reqs*).
- An integration must **not** add, pin, or install any new package, and must **not** create or modify
  `requirements.txt` — `crm_common` makes this a hard req. Any capability an integration needs is
  built on packages the host already ships (`salesforce.plain`, for instance, forbids any Salesforce
  SDK and uses the host's `httpx`). If a provider genuinely cannot be reached with the host's
  packages, that is a host-manifest decision to raise with the user, not something an integration
  spec resolves on its own. **Known stale pin:** `requirements.txt` still carries `simple-salesforce`
  from the pre-refactor salesforce spec; it is dead residue — do not build on it, and remove it when
  convenient.
- If an SDK is genuinely in play it must already be in the host manifest; pin its exact API surface
  per *Pin the third-party SDK API surface* above — "available in the system" answers *whether* it is
  present, not *how* its API is shaped.

This keeps the renderer from inventing imports and keeps the host manifest the single source of truth
for what is installed.

## Probe for dirty / boundary records *before* authoring, not during render

The live-API cross-check in `integrations.md` § *Live API must be cross-checked* already mandates
boundary coverage (empty list, 404, 400/422, deliberate 401, multi-page). Do one more thing
**before authoring**: deliberately hunt for the boundary record shapes the mapping must absorb
(empty/null fields, missing lookup, malformed type) and confirm the mapping's `None`/empty-string
fallback covers each. These findings ground the mapping contract and the OpenAPI record schema's
dirty-data annotations — each becomes a spec decision, not a render-time surprise.

## Before you render — the real guard against a mid-render stop

This is a short reminder, not a substitute for the workflow. Follow `integrations.md`,
`integration-embedded.md`, and `integration-embedded-testing.md` **in order before** you reach this
point. The steps that actually prevent a mid-render stop are: pin the API surface in the OpenAPI file,
ground the mapping's fallbacks against real boundary records, and rely on the inherited `crm_common` /
`integration_testing` reqs for all cross-cutting behavior so it is in scope from functionality 1 (the
module itself authors none).

- The partition rule (for when you edit the **templates** — the per-provider module authors neither
  section): every `***implementation reqs***` entry about `:UnitTests:` lives **only** there (in
  `crm_common`), and every `:ConformanceTests:` fact **only** in `***test reqs***` (in
  `integration_testing`) — crossing them silently drops the requirement (`impl-reqs.md` § *Unit tests
  vs conformance tests*, one of the most common mistakes).
- Run `codeplain <provider>.plain --dry-run` and `plain-healthcheck` to catch spec-syntax,
  concept-resolution, and config-wiring errors. **Be clear about their limits:** neither runs the
  mapping, hits the live API, or exercises the integration, so neither can catch a mapping bug, a
  wrong pinned query, or a credential mismatch. A green dry-run does **not** mean a safe render.
- Run `analyze-func-specs` across the new specs to surface conflicts before rendering.

## Auto-loaded startup context (`@imports` — do not remove)

These `@`-imports load the full authoring context into every session, **uncapped** — the ~10K-char
SessionStart-hook output limit does **not** apply to CLAUDE.md imports. They expand the **live** files
at launch, so the context never drifts from source. The dynamic existing-integrations list is added
separately by `.claude/hooks/load-integration-context.sh`. Paths are relative to this file (repo root).

@.claude/skills/load-plain-reference/SKILL.md
@README.md
@plain/salesforce.plain
@plain/template/crm_common.plain
@plain/template/integration_testing.plain
@src/models/schemas.py
@src/services/ingest.py
@requirements.txt
@plain/config.yaml
@plain/resources/salesforce/openapi.yaml
@plain/resources/salesforce/contact-mapping.md
