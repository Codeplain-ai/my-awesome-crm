# 🦸 My Awesome CRM

> One contact list to rule them all. Ten CRMs walk into a bar, one tidy address book walks out.

You've got contacts in Salesforce. And HubSpot. And that one in Pipedrive your coworker swore by. And — wait, is "Jon Smith", "jon smith", and "J. Smith <jon@acme.com>" the *same person*? (Spoiler: yes. And we figured that out for you.)

**My Awesome CRM** is a contact-aggregation service that vacuums up people from a fleet of CRM providers, deduplicates the chaos, gently merges the duplicates, and hands you one clean, consolidated list behind a tidy little API.

---

## ✨ What it does

- 🔌 **Plug-and-play integrations** — drop a provider folder in, and it gets auto-discovered. No registry, no config, no ceremony.
- 🧹 **Smart de-duplication** — matches contacts by email first, then falls back to `name + phone`. "Bob", "bob ", and "BOB" are all just Bob.
- 🤝 **Non-destructive merging** — existing data wins; incoming data only fills in the blanks. Custom fields get a shallow merge so nothing precious is clobbered.
- 🔗 **Source tracking** — every contact remembers exactly which provider + external ID it came from, so re-syncs update instead of duplicate.
- 🖥️ **Built-in web UI** — open the root URL and click your way through discovery, ingestion, and the contact list. No auth, no setup.
- 📋 **Paginated, searchable contacts API** — because nobody wants to scroll through 40,000 rows.

## 🏢 Supported CRMs (10 and counting)

| | | |
|---|---|---|
| Salesforce | HubSpot | Pipedrive |
| Zoho | Copper | Close |
| Streak | Zendesk Sell | SugarCRM |
| Nimble | | |

Each one lives in `src/integrations/<provider>/` and just has to promise one thing: a `fetch_contacts()` function. Honor that contract and the host picks you up automatically. 🎉

## 🧰 Built with

- ⚡ **FastAPI** — the web framework
- 🐘 **SQLModel** + **SQLite** — models & storage
- 🪶 **Alembic** — migrations
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

- **http://localhost:8000/** — the built-in web UI (discover → ingest → browse contacts)
- **http://localhost:8000/docs** — the interactive Swagger playground

The server itself is **unauthenticated** — there's no `X-API-Key`. The only credentials in play are the per-provider ones each integration reads from the environment when it runs.

### ⚙️ Configuration

All optional:

| Variable | Default | What it does |
|---|---|---|
| `CRM_PORT` | `8000` | Port to serve on. |
| `CRM_DB_PATH` | `crm.db` | Where the SQLite file lives. |

Provider integrations read their own credentials from the environment (e.g. `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN` for Salesforce).

---

## 🎮 Taking it for a spin

The easiest way is the **web UI at http://localhost:8000/** — it discovers the
integrations, ingests them on a click, and shows the consolidated list. Or, from the terminal:

```bash
# See which integrations the host discovered
curl -X POST localhost:8000/ingest/discover

# Pull everyone in from Salesforce
curl localhost:8000/ingest/salesforce
# → {"integration":"salesforce","fetched":42,"created":40,"updated":2}

# Browse your shiny consolidated contacts
curl "localhost:8000/contacts?limit=10&q=acme"
```

## 🗺️ The grand tour

```
src/
├── main.py              # 🚪 FastAPI app + startup ritual + web UI route
├── config.py            # ⚙️  Lazy-loaded settings
├── db.py                # 🐘 Engine & sessions
├── static/              # 🖥️  The single-page web UI (index.html)
├── api/                 # 🛣️  Routes: health, contacts, ingest
├── services/
│   ├── ingest.py        # 🔍 Discovery + orchestration
│   └── dedup.py         # 🧹 The "are these the same human?" brain
├── models/              # 📦 DB tables + API schemas
├── repositories/        # 🗄️  Data access
└── integrations/        # 🔌 One folder per CRM provider
```

## 🧪 Tests

There's a test for basically everything — APIs, services, repositories, and every single integration's client + mapping.

```bash
pytest
```

---

## 🤓 How the dedup magic works

1. **Got an email?** Lowercase + trim it → that's your key. Done.
2. **No email?** Fall back to `name:<lowercased name>|phone:<digits-only>`.
3. **Got neither?** We shrug and treat it as a brand-new contact.

When a match is found, we **merge gently**: your existing data stays put, and the newcomer only gets to fill in empty fields. Custom fields are merged key-by-key. Everybody wins. 🕊️

---

<sub>Made with FastAPI, a healthy fear of duplicate contacts, and a little bit of ✨.</sub>
