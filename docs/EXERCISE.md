# 🛠️ Workshop: build a CRM integration with integration-forge

> **Goal.** Learn to **use integration-forge**, **run its workflow**, and **produce `***plain`
> specs** for a real CRM integration — driving your coding agent entirely with prompts. The
> deliverable of this exercise is the **specs** (the `.plain` module + its `resources/`), not
> hand-written Python: you author the specs with the forge, then let the `codeplain` renderer
> generate the integration code from them.
>
> - **Part 1** — build a **HubSpot** integration that syncs **contacts**.
> - **Part 2** — **maintain / extend** it to also sync **accounts** (HubSpot "companies").

This is a hands-on exercise. You run the prompts; the agent does the authoring, grounded by the
rules baked into this repo. Everything you type is plain English — there are no magic commands to
memorize.

---

## 🤔 What is integration-forge?

integration-forge is a set of **skills, rules, and project memory** that plug into your coding agent.
Its purpose — and the thing that matters most in this exercise — is that it **produces `***plain`
specs**: a correct, well-structured `.plain` module and its `resources/` (the OpenAPI contract, the
mapping doc). The workflow (interview → ground against the live API → author → verify) exists only to
get those specs right; the **specs are the deliverable**. The rendered Python under
`src/integrations/` is just what `codeplain` generates *from* the specs — throwaway output you never
edit by hand.

Keep that lens the whole way through: at every step, ask *"what did this add to the `.plain` spec and
its `resources/`?"* — that artifact is the point.

In this repo the pack ships for every major agent:

| Agent | Where the pack lives |
|---|---|
| Claude Code | `.claude/` (`skills/`, `rules/`, `hooks/`, `settings.json`) + `CLAUDE.md` |
| opencode | `.opencode/` (see `.opencode/.plain-forge/manifest.json`) |
| Codex / others | `AGENTS.md` (+ the shared `rules/`) |

The pack encodes the whole spec-authoring method: how to interview you for the parts the codebase
can't tell it, how to ground the contract against the provider's **live API**, how to lay out the
`.plain` module and its `resources/`, and how to verify the specs render cleanly.

> **Note for this project.** The generic `/forge-plain` slash-command (and the other `/add-*`
> authoring commands) are intentionally **disabled here** — see the *"Skills to refrain from using"*
> section of `CLAUDE.md`. In this workshop the workflow is **prompt-driven**: you describe what you
> want, and the embedded rules steer the agent to author the specs directly. That's the whole point
> of the exercise — you experience the forge through natural conversation.

---

## ✅ Prerequisites

Before you start, make sure you have:

1. **A coding agent with this repo open** — Claude Code, opencode, or Codex. The agent must load
   this repo's instructions (`CLAUDE.md` / `AGENTS.md`) and skills/rules automatically on start.
2. **The `codeplain` CLI on your PATH** and a **`CODEPLAIN_API_KEY`** exported in your shell. This
   is what renders `.plain` specs into code. Check with:
   ```bash
   command -v codeplain && [ -n "$CODEPLAIN_API_KEY" ] && echo "ready"
   ```
3. **Python 3.12 or newer** — needed to run the host and its tests. `./scripts/start.sh` will set
   up the virtualenv for you.
4. **A HubSpot Private App access token** — put it in a repo-root `.env` as
   `HUBSPOT_ACCESS_TOKEN=...` (the `.env` is gitignored — never commit a token). This is **required
   to render**: `codeplain` runs the integration's conformance tests as part of rendering, and the
   conformance runner needs the `.env` credentials to be present (it fails fast otherwise). The same
   token is what live ingestion uses at runtime. It's also what lets the agent run the optional
   *live-API cross-check* against your real portal during authoring — but even if you author
   "docs-grounded" (skipping the cross-check), the token must still be in `.env` before you render.

Give the host a spin first so you know what "working" looks like:

```bash
./scripts/start.sh          # macOS / Linux  (Windows: .\scripts\start.ps1)
# then open http://localhost:8000/  and click Discover → Ingest → Records
```

---

## 🧭 How the pieces fit (30-second mental model)

- The **host** is a FastAPI app in `src/`. It has a generic record store and auto-discovers any
  plug-in under `src/integrations/<provider>/`.
- Each integration plug-in promises just two things: a module-level `DATA_TYPE` and a
  `fetch(get_stored)` function that returns a list of records to store.
- You **don't write that plug-in by hand.** You write a `.plain` **spec** under `plain/` (e.g.
  `plain/hubspot.plain`) plus its `resources/` (an OpenAPI file for the API surface, a mapping doc
  for the field-by-field contract). The `codeplain` renderer turns the spec into the plug-in under
  `src/integrations/hubspot/`.
- The `.plain` files are the **source of truth**. To change behavior you edit the spec and
  re-render — never edit generated code.

`plain/salesforce.plain` is the **reference example** — a complete, working integration you can read
end to end while you do this exercise.

---

## 🚀 Part 1 — build the HubSpot contacts integration

Start a fresh agent session in this repo and drive it with the prompts below. **Read what the agent
does between prompts** — that's where the learning is.

### Step 1 — kick it off

Paste this prompt:

> **`Let's create a new integration for HubSpot. It should sync contacts.`**

Watch what the forge does:

- It creates the empty module `plain/hubspot.plain` with just the frontmatter first.
- It checks the repo `.env` for existing HubSpot credentials.
- It **web-searches and fetches HubSpot's live API docs** to ground the contract (it does not
  author from memory).

### Step 2 — answer the interview (one question at a time)

The forge asks you **3–5 questions**, one at a time, about the things the codebase can't tell it.
For HubSpot you'll be asked things like:

- **Auth method** — pick **Private App token** (`Authorization: Bearer $HUBSPOT_ACCESS_TOKEN`).
- **Which contact properties** to pull (e.g. `email, firstname, lastname, jobtitle, company`).
- **Live cross-check** — provide a token now, or proceed docs-grounded and probe later.
- **Scope** — active contacts only, or include archived.

After **each** answer, the agent folds your choice into the spec before asking the next question.
There are no wrong answers here — choose what a real sync would want.

### Step 3 — let it finish authoring

Once the interview is done, the forge will have produced:

- `plain/hubspot.plain` — 5 definitions, 1 conformance test req, 3 functional specs (mirroring
  `salesforce.plain`).
- `plain/resources/hubspot/openapi.yaml` — the entire HubSpot API surface it calls.
- `plain/resources/hubspot/contact-mapping.md` — the field-by-field mapping contract.

It then runs a **dry-run** and the **`plain-healthcheck`** to prove the specs resolve. If anything
is off, ask the agent to fix the spec (never the generated code).

### Step 4 — render the integration

Make sure `HUBSPOT_ACCESS_TOKEN` is in your repo-root `.env` first (see Prerequisites) — rendering
runs the conformance tests, and the conformance runner requires those credentials to be present.
Then ask the agent to render, or do it yourself:

```bash
cd plain
codeplain hubspot.plain
```

This generates `src/integrations/hubspot/`. The render is only green once the specs resolve **and**
the generated integration's tests pass under `codeplain`.

### Step 5 — verify it works

Start the host and use the built-in web UI — no `curl` needed:

```bash
./scripts/start.sh          # macOS / Linux  (Windows: .\scripts\start.ps1)
```

Then open **http://localhost:8000/** in your browser and:

1. Click **Discover** — **hubspot** now appears in the list of integrations.
2. Click **hubspot** to run its sync.
3. Browse the **Records** list — the pulled contacts show up as `contact` records.

The integration reads `HUBSPOT_ACCESS_TOKEN` from the environment when it runs, so clicking
**hubspot** pulls live contacts and stores them. If the variable is missing or empty it fails with a
`RuntimeError` naming the missing variable — exactly the behavior the spec promises.

✅ **Part 1 done** when `hubspot.plain` renders green and **hubspot** appears and syncs contacts in
the UI.

---

## 🧩 Part 2 — maintain it: extend the sync to accounts

Real integrations grow. Now you'll **extend** the sync to also cover **accounts** (HubSpot calls
them *companies*, at `/crm/v3/objects/companies`). The host store is type-agnostic — a single
integration can emit more than one `data_type`; its `fetch` returns records tagged with their
`data_type` and `data`, and the host stores each verbatim.

Frame this as the start of a **shared capability**: accounts should eventually be a general
function that *every* integration supports (just like contacts) — but for this exercise you scope
the actual work to HubSpot only. Telling the forge the intended direction lets it factor the specs
sensibly (e.g. via the shared `crm_common` template) instead of baking account logic solely into
the HubSpot module.

In the same (or a new) session, prompt:

> **`Accounts should become a general capability that all integrations support, the same way
> contacts already are — but for now, only implement it for HubSpot. Extend the HubSpot integration
> to also sync accounts (HubSpot companies) under the data_type "account", and keep the existing
> contact sync working.`**

What to expect from the forge this time:

- It re-grounds against the **companies** endpoint (new live-doc fetch), adding it to
  `resources/hubspot/openapi.yaml`.
- It adds an **account mapping** contract (a new `resources/` doc) and the concepts/specs for it,
  following the same shape as the contact mapping.
- It updates `fetch(get_stored)` so a single run returns **both** contact and account records, each
  tagged with its `data_type`.
- It re-runs the dry-run + healthcheck.

Then re-render:

```bash
cd plain && codeplain hubspot.plain
```

Restart the host, open **http://localhost:8000/**, and click **hubspot** again. In the **Records**
list you should now see both `account` and `contact` records from that single run.

✅ **Part 2 done** when one click on **hubspot** stores both `contact` and `account` records and the
earlier contact behavior still passes.

---

## 🔁 Start over / clean up

To redo the exercise from scratch, run the cleanup script with the integration name — it removes
every file and folder matching that name (the `.plain` module, its `resources/`, the generated
plug-in, `plain_modules/`, and `conformance_tests/`) and resets the local `crm.db`:

```bash
./scripts/cleanup.sh hubspot
```

Then start the exercise again from Part 1.

---

## 💡 Tips for getting the most out of the forge

- **Let it interview you.** The one-question-at-a-time flow is deliberate — each answer shapes the
  next question. Don't pre-dump every decision in the first prompt.
- **Read the diffs.** After each answer, look at what changed in `plain/hubspot.plain` and its
  `resources/`. Seeing the spec grow is the point of the exercise.
- **Change behavior in the spec, not the code.** If the rendered plug-in does the wrong thing, fix
  the `.plain` file (or its linked resource) and re-render. Edits to `src/integrations/` are
  overwritten on the next render.
- **Compare against the exemplar.** Keep `plain/salesforce.plain` and its `resources/salesforce/`
  open — the HubSpot spec should end up structurally identical.
- **Provider docs win over memory.** If you ever disagree with the agent about the API shape, point
  it at the live HubSpot docs — grounding against the real API is a core rule of the forge.
