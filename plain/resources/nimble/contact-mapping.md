# Nimble Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Nimble integration. The input is
a dict shaped like one entry of the `resources[]` array returned by the Nimble REST API contacts
list endpoint (see the `ContactRecord` schema in `resources/nimble/openapi.yaml`). Business data
lives under the record's `fields` map, where each field key (e.g. `first name`, `last name`,
`email`, `phone`, `title`, `company`) maps to an ARRAY of entry objects, each with a `value` (and
optional `modifier`/`group`/`label`). The output is a contact `data` dict — the conventional
contact shape the host stores verbatim under the `data` of a `contact` record. It has exactly the
keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Reading a field value

For every field consumed below, the value is the `value` of the FIRST entry in that field's array.
A field is treated as **missing** (yielding `None` or an empty string before fallback) when its key
is absent, its array is empty, the first entry has no `value`, or that `value` is null or empty
after trimming. The integration never reads beyond the first entry of a field's array.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `nimble`. |
| `external_id` | `id` | The record's `id`, or `None` when missing. |
| `full_name` | first value of `fields["first name"]` + first value of `fields["last name"]` | See *full_name derivation* below. |
| `primary_email` | first value of `fields["email"]` | See *primary_email* below. |
| `job_title` | first value of `fields["title"]` | The first `title` entry value, or `None` when missing or empty. |
| `company_name` | first value of `fields["company"]` | The first `company` entry value, or `None` when missing or empty. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, it is an
empty string. The mapping never raises for a missing name.

1. The first value of `fields["first name"]` and the first value of `fields["last name"]` joined by
   a single space, each treated as empty when missing or null, with surrounding whitespace stripped
   — used when that joined value is non-empty.
2. Otherwise the first value of `fields["email"]`, trimmed — used when non-empty. (Nimble contacts
   are commonly identified by email when no name is recorded.)
3. Otherwise the first value of `fields["company"]`, trimmed — used when non-empty.
4. Otherwise an empty string.

## primary_email

- `primary_email` is the first value of `fields["email"]`, lowercased and trimmed.
- A missing or empty `email` maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` captures the record-level `record_type` value when present and non-null, copied
  verbatim under the key `record_type`, so the contact's Nimble kind is preserved.
- The consumed business field keys (`first name`, `last name`, `email`, `phone`, `title`,
  `company`) are not copied into `custom_fields`.
- The `fields` map itself and the record-level `id` are not copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
