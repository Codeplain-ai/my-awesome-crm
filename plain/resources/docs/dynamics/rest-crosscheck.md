# Dynamics 365 (Dataverse) Web API — cross-check snapshot

Grounding for `dynamics.plain`. Captured from the provider docs **and** verified against the
live org (read-only GET probes, plus the OAuth token POST which is the credential gate) during
authoring on 2026-06-09. Where docs and live API disagreed, the **live API wins** and the
divergence is noted. All credentials, tokens, and PII are redacted from the saved fixtures.

Live org probed: `https://org427d9ce3.crm4.dynamics.com` (341 contacts).

## Auth — OAuth 2.0 client credentials (Azure AD v2, server-to-server)
- Token endpoint: `POST https://login.microsoftonline.com/{DYNAMICS_TENANT_ID}/oauth2/v2.0/token`
- Body (form-encoded): `grant_type=client_credentials`, `client_id`, `client_secret`,
  `scope={DYNAMICS_RESOURCE_URL}/.default`.
- `{DYNAMICS_RESOURCE_URL}` is the org/environment URL, e.g. `https://org427d9ce3.crm4.dynamics.com`.
- The v2 endpoint uses **`scope`** (`<env-url>/.default`), NOT the v1 `resource` parameter.
- Live probe: token request → **HTTP 200**. Response JSON keys:
  `access_token`, `token_type` (`Bearer`), `expires_in` (3599), `ext_expires_in`.
- The flow issues **no refresh token**. A fresh token is acquired on every `fetch_contacts()` call.
- Unlike Salesforce, the token response carries **no `instance_url`** — all API calls use
  `{DYNAMICS_RESOURCE_URL}` directly as the base.
- Docs: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/authenticate-oauth

## Contacts read — `GET {DYNAMICS_RESOURCE_URL}/api/data/v9.2/contacts`
- Headers: `Authorization: Bearer <access_token>`, `Accept: application/json`,
  `OData-MaxVersion: 4.0`, `OData-Version: 4.0`.
- API version `v9.2` probed and returns 200; pinned for stability.
- Query options used:
  - `$select=contactid,fullname,firstname,lastname,emailaddress1,telephone1,mobilephone,jobtitle,department`
  - `$expand=parentcustomerid_account($select=name)` to pull the parent **account** name.
- Live record keys confirmed present: `@odata.etag`, `contactid`, `fullname`, `firstname`,
  `lastname`, `emailaddress1`, `telephone1`, `mobilephone`, `jobtitle`, `department`,
  `parentcustomerid_account`.
- Response envelope keys: `@odata.context`, `value` (array), and `@odata.nextLink` (only when more
  pages exist).
- Fixture: `resources/fixtures/dynamics.contacts.list_page.json`.

### Note #1 — per-record metadata uses `@odata.*` keys
- Every record carries `@odata.etag` (and the envelope carries `@odata.context` / `@odata.nextLink`).
- These are the OData metadata envelope (the analogue of Salesforce's `attributes`) and must be
  excluded from `custom_fields`.

### Note #2 — company name is an expanded nested object
- `parentcustomerid` is a **polymorphic customer lookup** (target can be an account OR a contact).
- Expanding `parentcustomerid_account($select=name)` returns the parent **account** as a nested
  object `{"accountid": "...", "name": "..."}` on the record.
- When the contact has no parent account, the expanded navigation property is **omitted** from the
  JSON (it is not present as `null`) — so the mapping must treat a missing key as "no company".
- The nested `accountid` is also not copied into `custom_fields`; only `name` is consumed.

## Pagination — `@odata.nextLink` (absolute URL), NOT `$skip`
- Dataverse does **not** support `$skip`. Paging is driven by `@odata.nextLink`.
- Default page size is **5000** records; `Prefer: odata.maxpagesize=N` (1–5000) can request smaller
  pages. Do **not** combine `$top` with `odata.maxpagesize` (`$top` is ignored).
- `@odata.nextLink` is a **fully-qualified absolute URL** with an opaque `$skiptoken`. Follow it
  **verbatim** with a GET (same headers) — never modify, re-encode, or append query options.
- Stop when a response has no `@odata.nextLink`.
- Live probe: forced `Prefer: odata.maxpagesize=2` → page 1 had 2 records + `@odata.nextLink`;
  following it verbatim returned page 2 (2 records) + a further `@odata.nextLink`. Confirmed working.
- Docs: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/query/page-results

## Error envelope — `{ "error": { "code", "message" } }`
- Dataverse error bodies are a JSON object with a nested `error` holding `code` and `message`.
- Live probes:
  - Bad `$select` field → **HTTP 400**.
    Fixture: `resources/fixtures/dynamics.contacts.400_invalid_field.json`.
  - Nonexistent record retrieve (all-zero GUID) → **HTTP 404**.
    Fixture: `resources/fixtures/dynamics.contact.404_not_found.json`.
  - Deliberately invalid bearer token → **HTTP 401**.
    Fixture: `resources/fixtures/dynamics.contacts.401_invalid_token.json`.

## Dirty data — the mapping-fail hunt (live org, 341 contacts)
- **Nameless contacts (the dominant case).** `fullname eq null` → **142**. ALL 142 also have
  `firstname` AND `lastname` null (`fullname eq null and firstname eq null and lastname eq null` →
  **142**), so **none** are recoverable via a first/last fallback. Of those 142: **38** have an
  email, **0** have a phone, 104 are fully empty. The remaining **199** contacts have a usable name.
- **Decision (with user, 2026-06-09): skip-and-log.** A contact that cannot produce a non-empty
  `full_name` (all of `fullname`/`firstname`/`lastname` empty) is dropped with a warning naming its
  `contactid`; the rest of the batch succeeds. This drops the 142 nameless records and syncs 199.
  Chosen for consistency with the Salesforce integration and to keep nameless junk out of the CRM.
- **Email.** `emailaddress1 eq null` → **298** (most contacts have no email); those map to
  `primary_email = None` — not a failure.
- **Parent account.** `_parentcustomerid_value eq null` → **339**; those map to `company_name = None`
  — not a failure.
- **Malformed email.** Scanned all 43 non-null emails through the host's `email-validator`
  (deliverability off, matching `EmailStr`): **0 malformed**. The host-crash guard is still applied
  defensively — the host models `:IncomingContact:.primary_email` as `EmailStr`
  (`src/models/schemas.py`) and its ingest loop (`src/services/ingest.py`) rolls back and re-raises on
  the first bad record, so any future malformed email would abort the whole ingest after
  `fetch_contacts()` returns where skip-and-log can't see it. The mapping emits `primary_email` only
  when the value validates; otherwise `None` with a warning naming the `contactid`. See the folded-back
  lesson in CLAUDE.md.
- Non-mapping errors (missing credentials, auth failure, transport/HTTP errors) are never swallowed —
  they propagate to the caller.
