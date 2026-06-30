# Close Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Close integration. The input is a
dict shaped like one entry of the `data[]` array returned by the Close contacts list API (see the
`ContactRecord` schema in `resources/close/openapi.yaml`). A Close contact belongs to exactly one
Lead and may carry multiple `emails[]` and `phones[]`. The output is a contact `data` dict — the
conventional contact shape the host stores verbatim under the `data` of a `contact` record. It has
exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `close`. |
| `external_id` | `id` | The record's `id`, or `None` when missing. |
| `full_name` | `name`, else the first `emails[]` entry's `email` | See *full_name derivation* below. |
| `primary_email` | the first `emails[]` entry's `email` | See *primary_email* below. |
| `job_title` | `title` | The `title` value, or `None` when missing or empty. |
| `company_name` | the parent lead/organization name | The lead or organization display name if available on the record; otherwise `None`. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, it is an
empty string. The mapping never raises for a missing name.

1. The `name` value, trimmed — used when non-empty.
2. Otherwise the first `emails[]` entry's `email` value, trimmed — used when non-empty. (Close
   contacts can be name-less, and an email is the next most identifying field.)
3. Otherwise an empty string.

## primary_email

- `primary_email` is the first `emails[]` entry's `email` field, lowercased and trimmed.
- A missing or empty `emails[]` array, or a missing or empty `email` on its first entry, maps to
  `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.
- Note: when the first `email` is used as the `full_name` fallback (a name-less contact),
  `full_name` takes that raw email string while `primary_email` is the same value lowercased and
  trimmed.

## custom_fields rules

- `custom_fields` captures the Close provenance fields `lead_id`, `organization_id`, `date_created`
  and `date_updated` from the input record, each copied verbatim when present and non-null.
- `id` is never copied — it duplicates `external_id`.
- The consumed business fields (`name`, `title`, `emails`, `phones`) are not copied into
  `custom_fields`.
- Presentation and audit fields (`display_name`, `created_by`, `updated_by`) are not copied into
  `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
