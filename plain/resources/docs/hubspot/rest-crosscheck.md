# HubSpot Contacts REST API — live cross-check

Grounding notes for `resources/hubspot/openapi.yaml`. The provider's reference docs
(`developers.hubspot.com/docs/reference/api/crm/objects/contacts`) sit behind a login wall — a
`fetch` of the reference page 307-redirects to `app.hubspot.com/myaccounts`. So the API surface
below was grounded by **read-only GET probes against the live HubSpot account** using the
`HUBSPOT_ACCESS_TOKEN` Private App token. Where memory of the docs and the live API could disagree,
the live API wins.

## Probes run (all read-only GET)

| # | Request | Result |
|---|---------|--------|
| 1 | `GET /crm/v3/objects/contacts?limit=2&properties=firstname,lastname,email,jobtitle,company` | `200` — `results[]` with nested `properties`, plus `paging.next.after` |
| 2 | Same, following the `after` cursor to the last page | `200` — `paging` object **absent** on the final page |
| 3 | `GET /crm/v3/objects/contacts?limit=1` with a bad token | `401` — `{status, message, correlationId, category: INVALID_AUTHENTICATION}` |
| 4 | `GET /crm/v3/objects/contacts?limit=-5` | `400` — `{... category: VALIDATION_ERROR, context.limit}` |
| 5 | `GET ...&limit=100&properties=...` — full account scan | `200` — 3 contacts, one with `firstname`/`lastname` both `null` |
| 6 | `GET ...&properties=this_prop_does_not_exist_xyz` | `200` — unknown property silently ignored |

## Findings folded into the OpenAPI

- **Auth**: static `Authorization: Bearer <token>` (Private App). No token-exchange / refresh step,
  unlike Salesforce's client-credentials flow.
- **Host**: single global host `https://api.hubapi.com`. No per-account instance URL — so no
  endpoint env var is needed (the token selects the account).
- **Endpoint**: `GET /crm/v3/objects/contacts`. API version `v3` is in the path, not a header.
- **Response shape**: business fields live inside a nested `properties` object, not flat. Top-level
  carries `id`, `createdAt`, `updatedAt`, `archived`, `url`. `id == properties.hs_object_id`.
- **Pagination (docs-vs-live)**: cursor-based via `paging.next.after`; the `paging` object is
  **absent** on the final page (not `paging.next` merely missing). The response also carries a
  `paging.next.link`, but the live API returns it with a differently-ordered path
  (`/crm/objects/v3/contacts`) — so the integration follows the **`after` cursor** against the
  canonical `/crm/v3/objects/contacts` path, never the `link` verbatim.
- **No compound name**: there is no `Name` field; `full_name` is derived from `firstname` +
  `lastname`.
- **Dirty data**: a live contact has `firstname` and `lastname` both `null` (email present). Any
  requested property can be `null`. Email is not guaranteed valid. The mapping absorbs all of this
  best-effort (`None` / empty-string fallbacks); the host stores the result verbatim.
- **Archived**: the list endpoint returns only active contacts (`archived=false`) by default; the
  integration pulls active only, so no `archived=true` pass is made.
- **Error envelope**: a JSON **object** `{status, message, correlationId, category, context?}` —
  contrast Salesforce, whose error body is a JSON array.
- **Unknown property tolerance**: requesting a non-existent property returns `200` (ignored), so the
  pinned property list is safe across accounts.

Fixtures captured under `resources/hubspot/fixtures/` (no credentials present in any response body).
