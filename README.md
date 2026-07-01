<p align="center">
  <img src="assets/mac.png" alt="mac" width="600" />
</p>


# My Awesome CRM

> One store to hold them all. Ten CRMs walk into a bar, one tidy little database walks out.

You've got contacts in Salesforce. And Dynamics. And that one in Pipedrive your coworker swore by. **My Awesome CRM** vacuums people out of a fleet of CRM providers and parks them in one simple, generic store behind a tidy little API — so everything lives in one place you can actually query.

---

## ✨ What it does

- 🔌 **Plug-and-play integrations** — drop a provider folder in, and it gets auto-discovered. No registry, no config, no ceremony.
- 🗃️ **Generic, type-agnostic storage** — every row is just a `data_type` (e.g. `"contact"`), the `source` that produced it, and a free-form JSON `data` payload. The store doesn't care what shape your records are.
- ↩️ **Idempotent re-syncs** — each integration owns its own rows. Re-running it replaces what it stored last time, so syncing twice never duplicates.
- 👀 **Read-back callback** — when an integration runs, the host hands it a callback to read everything already stored for a `data_type`, so the integration can do whatever it likes with the existing data.
- 🖥️ **Built-in web UI** — open the root URL and click your way through discovery, ingestion, and the record list. No auth, no setup.
- 📋 **Paginated records API** — browse everything, or filter to a single `data_type`.

> **Heads up:** there is intentionally **no deduplication or merging** in the host anymore. Records are stored verbatim. If a provider needs to reconcile against what's already there, that logic lives inside the integration — the host just stores what it's handed.

## 🏢 Supported CRMs (10 and counting)

| | | |
|---|---|---|
| Salesforce | Dynamics365 | Pipedrive |
| Zoho | Copper | Close |
| Streak | Zendesk Sell | SugarCRM |
| Nimble | | |

Each one lives in `src/integrations/<provider>/` and just has to promise two things:

```python
DATA_TYPE = "contact"            # what kind of record this integration produces

def fetch(get_stored):           # the host calls this to run the integration
    existing = get_stored("contact")   # read every stored row of this data_type
    ...                                # talk to the provider, do your thing
    return [ {...}, {...} ]             # the data payloads to store (verbatim)
```

Honor that contract and the host picks you up automatically. 🎉

### 🪄 Integrations are built with \*\*\*plain

You don't hand-write the integration code — you write a **[\*\*\*plain](https://plainlang.org)** spec and let the renderer generate it. Each provider is a `.plain` module under `plain/` (e.g. `plain/salesforce.plain`) that describes *what* the integration does; the generated plug-in lands in `src/integrations/<provider>/`. The `.plain` specs are the source of truth — the code under `src/integrations/` is a read-only artifact, so you change behavior by editing the spec and re-rendering, never by editing the generated files.

## 🧰 Built with

- ⚡ **FastAPI** — the web framework
- 🐘 **SQLModel** + **SQLite** — model & storage
- 🪵 **JSON logging** — for the observability nerds (we see you, and we love you)

---

## 🚀 Quickstart

```bash
# 1. Set up the environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Liftoff 🛫
uvicorn src.main:app --reload
```

Now visit:

- **http://localhost:8000/** — the built-in web UI (discover → ingest → browse records)
- **http://localhost:8000/docs** — the interactive Swagger playground

The server itself is **unauthenticated** — there's no `X-API-Key`. The only credentials in play are the per-provider ones each integration reads from the environment when it runs.

### ⚙️ Configuration

All optional:

| Variable | Default | What it does |
|---|---|---|
| `CRM_PORT` | `8000` | Port to serve on. |
| `CRM_DB_PATH` | `crm.db` | Where the SQLite file lives. |

Provider integrations read their own credentials from the environment (e.g. `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET` for Salesforce).

---

## 🎮 Taking it for a spin

The easiest way is the **web UI at http://localhost:8000/** — it discovers the
integrations, ingests them on a click, and shows the stored records. Or, from the terminal:

```bash
# See which integrations the host discovered
curl -X POST localhost:8000/ingest/discover

# Pull everyone in from Salesforce
curl localhost:8000/ingest/salesforce
# → {"integration":"salesforce","data_type":"contact","fetched":42,"stored":42,"replaced":40}

# Browse everything in the store
curl "localhost:8000/records?limit=10"

# Or just one data_type
curl "localhost:8000/records?data_type=contact&limit=10"
```

## 🗺️ The grand tour

```
src/
├── main.py              # 🚪 FastAPI app + startup ritual + web UI route
├── config.py            # ⚙️  Lazy-loaded settings
├── db.py                # 🐘 Engine & sessions
├── static/              # 🖥️  The single-page web UI (index.html)
├── api/                 # 🛣️  Routes: health, records, ingest
├── services/
│   └── ingest.py        # 🔍 Discovery + orchestration (run integration → store rows)
├── models/              # 📦 The generic Record table + API schemas
├── repositories/        # 🗄️  Data access (record_repo)
└── integrations/        # 🔌 One folder per CRM provider
```

## 🧪 Tests

There's a test for basically everything — APIs, services, repositories, and every single integration's client + mapping.

```bash
pytest
```

---

## 🗃️ How storage works

There's exactly one table, and it's deliberately dumb:

| Column | What it holds |
|---|---|
| `id` | Primary key. |
| `data_type` | The kind of record, e.g. `"contact"`. |
| `source` | Which integration produced the row. |
| `data` | The record itself, as free-form JSON. |
| `created_at` / `updated_at` | Timestamps. |

When you run an integration:

1. The host calls its `fetch(get_stored)`, handing over a callback to read everything already stored for a `data_type`.
2. The integration returns a list of `data` payloads.
3. The host **deletes that integration's previous rows** and inserts the fresh ones.

That's it. No matching, no merging, no "are these the same human?" guesswork — records are stored exactly as the integration hands them over. Re-running an integration is safe: it always replaces its own slice of the store. 🕊️

---

<sub>Made with FastAPI, a generic JSON column, and a little bit of ✨.</sub>
