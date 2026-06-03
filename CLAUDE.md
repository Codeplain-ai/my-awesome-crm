# my-awesome-crm — project memory

A Python 3.12 / FastAPI CRM host (`src/`) with an **embedded ***plain integration project** under
`plain/`. Each of the 10 providers is one root `.plain` module (`salesforce.plain`, `hubspot.plain`, …) that imports `crm_common` + `integration_testing` and emits a
runtime-discovered plug-in at `src/integrations/<name>/` exposing `fetch_contacts()`, which returns
normalized `:IncomingContact:` records.

The authoritative authoring rules live in `.claude/rules/`. **Read them and obey them first** — this
file does not restate them. It captures only the hard-won lessons the rules alone did not prevent,
and points back to the rule that governs each one.

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

## Pin the third-party SDK API surface — not just the provider's REST API

`integrations.md` § *Live API must be cross-checked* requires fetching and grounding the provider's
REST docs. That is not enough when the integration depends on a **client library**: the renderer will
otherwise guess constructor kwargs and method names and get them wrong.

**Rule:** for any SDK the integration depends on, fetch the library's own docs, save the snapshot
**alongside the provider docs** under `plain/resources/docs/<provider>/` (these are saved copies; host
source files are instead linked in place per `integration-embedded.md` § *Link host files at their
original path*), and pin the exact API surface — constructor kwargs, method names, token calls — in
`***implementation reqs***`.

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
