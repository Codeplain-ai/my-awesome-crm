# my-awesome-crm — project memory

A Python 3.12 / FastAPI CRM host (`src/`) with an **embedded ***plain integration project** under
`plain/`. Each of the 10 providers is one root `.plain` module (`salesforce.plain`, `dynamics.plain`, …) that imports `crm_common` + `integration_testing` and emits a
runtime-discovered plug-in at `src/integrations/<name>/` exposing `fetch()`, which returns
normalized `:IncomingContact:` records.

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

## Do not create a plan when writing plain specs

When authoring, editing, reviewing, or debugging any `.plain` content, **do not use the plan tool**
and do not produce a written plan. Spec authoring is governed end-to-end by the rules in
`.claude/rules/` and the lessons in this file — that workflow is the plan. Work the rules directly
instead of drafting a separate one.

## First step: create the empty `.plain` module with its frontmatter

When a user asks to create a new integration, the **very first action** — before any questions, host
discovery narration, or resource authoring — is to create the empty root `.plain` module at
`plain/<provider>.plain` containing **only** the YAML frontmatter (no spec sections yet). Mirror the
salesforce frontmatter exactly, but the `description` must be **integration-specific** (the provider,
its `src/integrations/<provider>/` plug-in, the `GET /ingest/<provider>` route, and what it pulls from
the provider's API). Template:

```yaml
---
import:
  - crm_common
  - integration_testing
description: "<Provider> Integration plug-in for the CRM backend. Adds src/integrations/<provider>/ so that GET /ingest/<provider> pulls Contact records from <provider> via its REST API and stores them as contact records in the host's generic record store."
---
```

## Ask the user at least 3-5 questions, one at a time — and write a spec after every answer

When building a new integration, **always ask the user at least 3-5 questions**. Ask them **one by one** — never batch them into a single multi-question prompt — so each
answer can inform the next question. Focus the questions on what the codebase cannot tell you: the
provider and its API, authentication and credentials, edge cases, and the batch failure policy for
dirty data. Everything the host already encodes is a deduction, not a question
(`integration-embedded.md` § *Discover before you ask*).

**After every answer, fold it into the `.plain` module (and its linked resources) BEFORE asking
the next question.** This is a hard rule inside the question loop, not a drafting phase you defer
until the interview is over. The loop is: *ask one question → user answers → write the spec → ask
the next question.* Each write must follow the **spec-writing style of `salesforce.plain`** (the
structural exemplar) exactly:

- Put the answer in the section it belongs to per the rules — `***definitions***` for a concept, `***test reqs***` for
  `:ConformanceTests:` facts, `***functional specs***` for functionalities.
- Mirror salesforce's shape: 5 definitions, 1 test req, 3 functional specs;
  the whole API surface behind `:<Provider>RestAPI:` in `resources/<provider>/openapi.yaml` and the
  mapping contract behind `:<Provider>ContactMapping:` in `resources/<provider>/contact-mapping.md`
  (see *Authoring the next integration* below).
- Inherit shared reqs silently from `crm_common` / `integration_testing` — never restate them.


## North star: render green on the FIRST `codeplain` run

The goal for every new integration is a clean render with **no mid-render stop-edit-rerender**. A
mid-render stop to edit specs is a **red flag**: a gap that should have been closed during authoring
leaked into the render. The whole rule set is built to make that gap impossible — live-API
cross-checks surface surprises before authoring (`integrations.md` § *Live API must be
cross-checked*), conformance runs end-to-end so nothing is deferred (`integration-embedded-testing.md`
§ *Staging model*), and all cross-cutting behavior lives in implementation reqs so it is in scope from
functionality 1 (`impl-reqs.md` § *Encapsulation warning*).

When a mid-render stop happens anyway, do not just patch and move on — **fold the fix back into the
specs AND into this file** so the next integration never hits it.

## Authoring the next integration — `salesforce.plain` is the structural exemplar

- **5 definitions** — provider id, credentials (env-var names), `:<Provider>RestAPI:` (OpenAPI link),
  `:<Provider>ContactMapping:` (mapping-doc link), and the integration concept itself.
- **1 test req** — conformance targets the provider's live API + the exact credential env-var names
  (identical to the names the runtime reads). Nothing else: folder location, framework, runner
  script, and pass criteria all come from the imported `integration_testing` template.
- **3 functional specs** — mapping, the `fetch()` composition, one-bullet wiring.

### The whole API surface lives in `resources/<provider>/openapi.yaml`, reached through one concept

Author the OpenAPI file **first**, from the live cross-check, and put **everything** in it: the auth
/ token endpoint with its request body, the query endpoint with the pinned query string as a schema
`const`, required headers, the API-version pin **with the reason**, the pagination envelope and its
mechanics, the record schema (with dirty-data annotations like "Email is NOT guaranteed valid"), the
error envelope, every docs-vs-live discrepancy ("live API wins"), and the saved probe fixtures wired
in via `examples.externalValue` — so the schema, fixtures, and `rest-crosscheck.md` form one
auditable bundle. Define `:<Provider>RestAPI:` in `***definitions***` carrying the **only** link to
the file; spec text then says "the token endpoint / query endpoint / pagination envelope of
`:<Provider>RestAPI:`" and **never** restates URLs, headers, fields, status codes, or continuation
markers (`nextRecordsUrl`, `@odata.nextLink`) inline. The pagination spec line is one sentence —
the exemplar's reads "Read every subsequent page per the pagination envelope of
:SalesforceRestAPI: until all pages are read." This per-provider folder layout deliberately
supersedes the flat `resources/<provider>.openapi.yaml` path in `integrations.md`'s artifact table
for this project; follow the folder layout.

### The mapping contract lives in `resources/<provider>/contact-mapping.md`, reached through one concept

The full field-by-field contract — mapping table, `full_name` derivation cascade, `primary_email`
validation (host's `email-validator`, deliverability off, emit `None` + warning, **not** a
record-skip), `custom_fields` rules, and the **exact** raise conditions (a `ValueError` only for a
missing provider id or an underivable `full_name`) — lives in the mapping doc, attached to a
`:<Provider>ContactMapping:` concept. Functional spec 1 is then "Implement
`:<Provider>ContactMapping:` as a pure function within the integration package" plus three deferral
bullets: the input shape (one `ContactRecord` of `:<Provider>RestAPI:`'s query response), the
output ("exactly those `:<Provider>ContactMapping:` pins"), and the `provider_id` literal.
**No function name, no file path** — and the host-contract email guard (see
*The host's own contract validation* below) is satisfied by copying the `primary_email` section of
`resources/salesforce/contact-mapping.md` into every new mapping doc until the guard is finally
hoisted into `crm_common`.

### `crm_common` owns the cross-cutting reqs — author only the per-provider residue

`template/crm_common.plain` now carries (a new integration must **not** restate any of it):

- the **skip-and-log batch policy** (generic, "provider-side id" abstracted),
- the **layout/identifier contract**: the only file contract is `src/integrations/<id>/__init__.py`
  exporting `fetch_contacts()` returning a **list** of dicts (each a valid `:IncomingContact:`,
  transformed by the host into `:Contact:`); internal organization is explicitly optional,
- the **integration `:UnitTests:` policy** (no network, single indirection seams, inline dict
  payloads, and the three mandatory coverage cases: skip-and-log, multi-page pagination,
  invalid-email-to-`None`),
- the **host ground-truth links**, linked once and in place: `../src/services/ingest.py` (on the
  `:Integration:` concept — discovery + invocation logic) and `../requirements.txt` (under the pip
  req — the no-re-pin source of truth). Never re-link or paraphrase these per-module.

A functional spec may still narrate per-record behavior that *is* that functionality's WHAT (the
`fetch()` composition names the skip-on-`ValueError` step inline) — the prohibition is on
restating the shared *policy* as a second implementation req.

### Never mandate internals — and know what the relaxation costs

Do not pin internal file names (`client.py`, `mapping.py`), private function names
(`_acquire_token`, `_get_json`), or per-file re-export wording. The contract is behavior plus the
single `__init__.py` export. Evidence this is real: after the mandates were removed, the re-render
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

- **Verify `.env` keys literally match the spec'd env-var names before rendering.** A
  `SALESFORCE_SLIENT_SECRET` typo (for `SALESFORCE_CLIENT_SECRET`) would have failed every live
  conformance attempt; the conformance runner is deliberately integration-agnostic and will not
  catch it — only the live `RuntimeError` would, mid-render.
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

## The timing trap: conformance is live and end-to-end from functionality 1

The renderer builds functional specs **one at a time, top to bottom**, and the renderer cannot see
specs that render later (`func-specs.md`: no knowledge of future specs). Every conformance test runs
`fetch_contacts()` **end-to-end against the live provider** — even for a spec that is "just" a pure
mapping function. So the full live path (auth, pagination, dirty-data handling) must already work
when the **first** functionality renders, because that functionality's conformance run already pulls
live records.

**Consequence:** any cross-cutting runtime behavior the live path needs cannot live in a later
functional spec. Put it in `***implementation reqs***` — in scope for **all** functionalities. A
functional spec carries only that functionality's WHAT. (Policy: `integration-embedded-testing.md` §
*Staging model*; `integrations.md` § *:ConformanceTests: always run against the live integration*.)

## Live data is dirty — every fallible per-record mapping needs an up-front batch policy

Live orgs contain malformed records, so any per-record mapping that **can raise** must be paired with
an explicit batch-level failure policy — **skip-and-log** vs **fail-fast** — decided **with the user
during authoring** and written as an **implementation req** so it is global from functionality 1. Do
not let the renderer discover the policy mid-run. For the mandatory transient-vs-permanent error
classification this builds on, see `integrations.md` § *Edge-case coverage*.

**Skip-and-log means a sync can legitimately drop a large fraction of the source records — that is
expected, not a bug.** The dominant skip cause is contacts with no usable name (the host requires a
non-empty `full_name` on `:IncomingContact:`). Concretely, `dynamics.plain` drops **142 of 341**
contacts on the probed org (all 142 have `fullname`/`firstname`/`lastname` all empty, none recoverable
via a first/last fallback), so **only ~199 sync by design**. If someone later reports "the integration
only imports ~60% of contacts / drops 40%", treat that as the **chosen** policy, not a defect — do not
"fix" it without re-asking the user. Each integration's exact dirty-data counts and the user's
decision live in its `plain/resources/docs/<provider>/rest-crosscheck.md` and
`plain/resources/fixtures/<provider>.*`; record the same for every new integration so the expected
drop is auditable instead of looking like data loss.

## The host's own contract validation is a per-record failure mode the skip-and-log does NOT catch

The integration's skip-and-log only wraps the mapping function *inside* `fetch_contacts()`. But the
host validates every emitted record by constructing `:IncomingContact:` from it (`IncomingContact(**raw_item)`
in `src/services/ingest.py`), and that loop **rolls back and re-raises on the first failure** — so one
record the host rejects aborts the *entire* ingest with zero writes, and it happens *after*
`fetch_contacts()` returns, where skip-and-log can't see it. Concretely, `primary_email` is typed as
`EmailStr` (`src/models/schemas.py`), so a single live contact with a malformed email (e.g. a `&` in
the domain) crashed the whole Salesforce ingest after a clean render (2026-06-08).

(`integrations.md` § *Live API must be cross-checked*) — query for malformed/boundary values of every
host-validated field, not just empty/null required ones — so the host's contract is satisfied from
functionality 1 instead of discovered as a post-render crash.

**This is cross-cutting, not Salesforce-specific.** Every integration emits `:IncomingContact:` and
every one is exposed to the same crash, so the guard belongs wherever it applies to all of them:

- **The host schema is the field inventory.** `src/models/schemas.py` (the `:IncomingContact:` model)
  is the single source of truth for *which* fields the host validates and *how* — read it and mirror
  each constraint in the mapping; never reconstruct the list from memory. Today that is the `EmailStr`
  on `primary_email` and the non-empty `full_name`, but the schema is authoritative if it changes.
- **Reuse the host's own validator**, never a hand-rolled regex — it is the only thing guaranteed to
  agree with what `:IncomingContact:` will accept. `email-validator` is already a host dependency
  (`integration-embedded.md` § *No host-overlapping reqs* — do not re-pin it).
- **The durable home is a shared `***implementation reqs***` entry in `template/crm_common.plain`**, so
  every integration inherits the guard from functionality 1 instead of each one re-discovering the
  crash. A per-integration fix (as done for Salesforce on 2026-06-08, confirmed working) unblocks one
  provider but leaves the rest latent — prefer the shared req when fixing this class of bug broadly.
- **Current state (2026-06-12):** the guard is still per-provider. In the optimized shape it lives
  inside the provider's mapping contract doc (`resources/salesforce/contact-mapping.md`
  § *primary_email validation*); `dynamics.plain` still carries it as a local implementation req.
  Every new integration must copy the mapping-doc section until the `crm_common` hoist happens.

## Pin the third-party SDK API surface — not just the provider's REST API

`integrations.md` § *Live API must be cross-checked* requires fetching and grounding the provider's
REST docs. That is not enough when the integration depends on a **client library**: the renderer will
otherwise guess constructor kwargs and method names and get them wrong.

**Rule:** for any SDK the integration depends on, fetch the library's own docs, save the snapshot
**alongside the provider docs** under `plain/resources/docs/<provider>/` (these are saved copies; host
source files are instead linked in place per `integration-embedded.md` § *Link host files at their
original path*), and pin the exact API surface — constructor kwargs, method names, token calls — in
`***implementation reqs***`.

## Declare which dependencies are already available in the system — don't assume

The host environment (`requirements.txt`) is the **only** set of packages the rendered integration
can rely on. The renderer cannot see what is installed; if the specs don't say it, it will guess —
and a guess that names an absent package, or re-adds one the host already ships, surfaces only at
runtime (import error) or as an avoidable second pin. `integration-embedded.md` § *The host codebase
dictates the tech stack* makes the host manifest ground truth, and § *Discover before you ask*
requires reading it **before** the first authoring question; this lesson makes the result explicit in
the spec.

**Rule:** as part of host discovery, enumerate the dependencies already available in the system from
`requirements.txt`, and state them in the new integration's specs:

- In `***implementation reqs***`, name the host packages the integration **reuses as-is** (e.g.
  `requests`, `httpx`, `pydantic`) — these are already pinned by the host, so the integration must
  **not** re-pin or re-add them (`integration-embedded.md` § *No host-overlapping reqs*).
- Only a dependency the host does **not** already provide is added to `requirements.txt` with an
  explicit version pin, and that addition is called out in the spec (as `pipedrive.plain` does for
  its explicit `requests` pin). `salesforce.plain` deliberately adds nothing — it forbids any
  Salesforce SDK and uses the host's `requests`. **Known stale pin:** `requirements.txt` still
  carries `simple-salesforce` from the pre-refactor salesforce spec; it is dead residue, not an
  available-package signal — do not build on it, and remove it when convenient.
- For any newly added SDK, still pin its exact API surface per *Pin the third-party SDK API surface*
  above — "available in the system" answers *whether* it is present, not *how* its API is shaped.

This keeps the renderer from inventing imports and keeps the host manifest the single source of truth
for what is installed.

## Probe for dirty / boundary records *before* authoring, not during render

The live-API cross-check in `integrations.md` § *Live API must be cross-checked* already mandates
boundary coverage (empty list, 404, 400/422, deliberate 401, multi-page). An incident added
one thing the cross-check must do **before authoring**: deliberately hunt for a record that **fails
the mapping function** (empty/null required field, missing lookup, malformed type), and confirm the
chosen failure mode for it. Save every probe response under `plain/resources/fixtures/` with
credentials redacted. Each finding becomes a spec decision, not a render-time surprise.

## Before you render — the real guard against a mid-render stop

This is a short reminder, not a substitute for the workflow. Follow `integrations.md`,
`integration-embedded.md`, and `integration-embedded-testing.md` **in order before** you reach this
point. The steps that actually prevent the three incidents above are: pin the SDK surface, probe for
dirty data, and put all cross-cutting behavior in implementation reqs.

- Every `***implementation reqs***` entry about `:UnitTests:` lives **only** there, and every
  `:ConformanceTests:` fact **only** in `***test reqs***` — crossing them silently drops the
  requirement (`impl-reqs.md` § *Unit tests vs conformance tests*, one of the most common mistakes).
- Run `codeplain <provider>.plain --dry-run` and `plain-healthcheck` to catch spec-syntax,
  concept-resolution, and config-wiring errors. **Be clear about their limits:** neither executes the
  SDK, hits the live API, or sees dirty data, so neither can catch any of the three incidents above. A
  green dry-run does **not** mean a safe render.
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
