# Salesforce REST API — cross-check snapshot

Grounding for `salesforce.plain`. Captured from the provider docs **and** verified against the
live org (read-only GET probes) during authoring. Where docs and live API disagreed, the
**live API wins** and the divergence is noted. All credentials, tokens, and PII are redacted from
the saved fixtures.

## Auth — OAuth 2.0 client credentials (server-to-server)
- Token endpoint: `POST {SALESFORCE_ENDPOINT}/services/oauth2/token`
- Body (form-encoded): `grant_type=client_credentials`, `client_id`, `client_secret`.
- `{SALESFORCE_ENDPOINT}` is the org My Domain login host, e.g.
  `https://your-domain.develop.my.salesforce.com`.
- Live probe: token request → **HTTP 200**. Response JSON keys:
  `access_token`, `instance_url`, `id`, `token_type` (`Bearer`), `scope`, `issued_at`, `signature`.
- The flow issues **no refresh token**. A fresh token is acquired on every `fetch_contacts()` call.
- IMPORTANT: subsequent API calls use **`instance_url`** from the token response as their base, not
  `SALESFORCE_ENDPOINT`. On this org the two happened to be the same host, but they are not guaranteed
  to be — always follow `instance_url`.
- Docs: https://help.salesforce.com/s/articleView?id=xcloud.remoteaccess_oauth_client_credentials_flow.htm

## Contacts read — `GET {instance_url}/services/data/v60.0/query/?q=<SOQL>`
- Headers: `Accept: application/json`, `Authorization: Bearer <access_token>`.
- API version: the live org advertises versions up to **v66.0**; **v60.0** was probed and returns 200.
  We pin **v60.0** for stability.
- SOQL used:
  `SELECT Id, Name, FirstName, LastName, Email, Phone, MobilePhone, Title, Account.Name FROM Contact`
- Live `Contact` describe confirmed these field names exist:
  `Id`, `Name`, `FirstName`, `LastName`, `Email`, `Phone`, `MobilePhone`, `Title`, `AccountId`,
  `Department` (67 fields total).
- Query response envelope keys: `totalSize`, `done`, `records`, and `nextRecordsUrl` (only when
  `done` is `false`). Live org currently holds **20** contacts.
- Fixture: `resources/fixtures/salesforce.contacts.list_page.json`.

### Note #1 — per-record metadata is `attributes`, not an `@odata` key
- Every record carries an `attributes` object `{ "type": "Contact", "url": "..." }`.
- This is Salesforce's metadata envelope (the analogue of Dataverse's `@odata.*` keys) and must be
  excluded from `custom_fields`.

### Note #2 — company name is a nested object, not a flat field
- `Account.Name` is returned as a **nested object** on the record: `"Account": { "Name": "...",
  "attributes": {...} }`, or `null` when the contact has no parent account.
- The nested `Account.attributes` object is also metadata and must not leak into `custom_fields`.

## Pagination — `nextRecordsUrl`, NOT `$skip`
- When more pages exist, `done` is `false` and `nextRecordsUrl` holds the **relative path** of the
  next page (e.g. `/services/data/v60.0/query/01g...-2000`). Follow it against `instance_url`.
- Stop when a response has `done: true` (then there is no `nextRecordsUrl`).
- Default page size is 2000 records; the minimum forced batch size is 200.
- Live caveat: this org has only 20 contacts, so the live query returns a single page
  (`done: true`, no `nextRecordsUrl`) — forcing a smaller page is not possible (min batch 200).
  The integration still implements `nextRecordsUrl` following because production orgs exceed 2000.
- Docs: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_query.htm

## Error envelope — JSON list of `{errorCode, message}`
- Every error response body is a **JSON array** whose entries have `errorCode` and `message`.
- Live probes:
  - Bad `$select` field → **HTTP 400**, `errorCode: INVALID_FIELD`.
    Fixture: `resources/fixtures/salesforce.contacts.400_invalid_field.json`.
  - Nonexistent record retrieve → **HTTP 404**, `errorCode: NOT_FOUND`.
    Fixture: `resources/fixtures/salesforce.contact.404_not_found.json`.
  - Deliberately invalid bearer token → **HTTP 401**, `errorCode: INVALID_SESSION_ID`.
    Fixture: `resources/fixtures/salesforce.contacts.401_invalid_session.json`.

## Dirty data — the mapping-fail hunt
- Probe `SELECT COUNT() FROM Contact WHERE Name = null` → **0**. Salesforce derives the compound
  `Name` field from `LastName`, which is **required** on Contact, so a contact with an empty
  `full_name` cannot occur naturally on this org. The natural Dataverse failure mode (all of
  `fullname`/`firstname`/`lastname` null) has no Salesforce equivalent.
- Probe `SELECT COUNT() FROM Contact WHERE Email = null` → **2**. Email is optional, so
  `primary_email` is simply `null` for those records — this is **not** a mapping failure.
- Probe `SELECT COUNT() FROM Contact WHERE AccountId = null` → **0** on this org; when it is null,
  `company_name` is `null` (also not a failure).
- **Malformed email (found post-render, 2026-06-08).** A live contact has an `Email` with an invalid
  character in the domain (a `&`, e.g. `user@bad&domain.net`). The host models
  `:IncomingContact:.primary_email` as `EmailStr` (`src/models/schemas.py`), so it rejects the value,
  and the host's ingest loop (`src/services/ingest.py`) wraps the whole fetch in one try/except that
  **rolls back and re-raises** — one bad email aborts the entire ingest with zero records written.
  The integration's skip-and-log can't catch it (the crash is in the host, after `fetch_contacts()`
  returns). Decision (with user): the mapping emits `primary_email` only when the value is a valid
  email (checked with the host's `email-validator`, deliverability off, matching `EmailStr`);
  otherwise `None`, logging a warning naming the `Id`. The contact is kept (dedups by name+phone).
- Decision (with user): adopt **skip-and-log** as the global batch-failure policy anyway — defensive,
  consistent with the other integrations. A record whose `Id` is missing/empty, or whose `Name` and
  both name parts are empty, is dropped with a warning naming its `Id`; the rest of the batch
  succeeds. Non-mapping errors (missing credentials, auth failure, transport/HTTP errors) propagate.
