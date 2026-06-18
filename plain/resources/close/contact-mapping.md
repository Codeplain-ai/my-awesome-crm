# Close Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Close integration. The input is a
dict shaped like one entry of the `data[]` array returned by the Close contacts list API (see the
`ContactRecord` schema in `resources/close/openapi.yaml`). A Close contact belongs to exactly one
Lead and may carry multiple `emails[]` and `phones[]`. The output is an `IncomingContact` dict with
exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `close`. |
| `external_id` | `id` | Required — raise `ValueError` if missing or empty. |
| `full_name` | `name`, else the first `emails[]` entry's `email` | See *full_name derivation* below. |
| `primary_email` | the first `emails[]` entry's `email` | See *primary_email validation* below. |
| `phone` | the first `phones[]` entry's `phone` | The `phone` value of the first non-empty `phones[]` entry; otherwise `None`. |
| `job_title` | `title` | The `title` value, or `None` when missing or empty. |
| `company_name` | the parent lead/organization name | The lead or organization display name if available on the record; otherwise `None`. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. The `name` value, trimmed — used when non-empty.
2. Otherwise the first `emails[]` entry's `email` value, trimmed — used when non-empty. (Close
   contacts can be name-less, and an email is the next most identifying field.)
3. Otherwise raise `ValueError`.

## primary_email validation

- `primary_email` is the first `emails[]` entry's `email` field, lowercased and trimmed, but only
  when it is a valid email address; otherwise `None`.
- A missing or empty `emails[]` array, or a missing or empty `email` on its first entry, maps to
  `None`.
- A non-empty `email` that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.
- Note: when the first `email` is used as the `full_name` fallback (a name-less contact) but is not
  a valid email address, `full_name` still takes the raw email string while `primary_email` is
  `None`.

## custom_fields rules

- `custom_fields` captures the Close provenance fields `lead_id`, `organization_id`, `date_created`
  and `date_updated` from the input record, each copied verbatim when present and non-null.
- `id` is never copied — it duplicates `external_id`.
- The consumed business fields (`name`, `title`, `emails`, `phones`) are not copied into
  `custom_fields`.
- Presentation and audit fields (`display_name`, `created_by`, `updated_by`) are not copied into
  `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
