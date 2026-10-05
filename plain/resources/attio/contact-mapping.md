# Attio Person → contact-data mapping contract

The field-by-field contract for the pure mapping of the Attio integration. The input is a dict
shaped like one entry of the `data[]` array returned by the Attio records query for the `people`
object (see the `PersonRecord` schema in `resources/attio/openapi.yaml`). The output is a contact
`data` dict — the conventional contact shape the host stores verbatim under the `data` of a
`contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

In `PersonRecord`, every attribute under `values` is an array of value objects, and an attribute
with no value is an empty array. "The first value" below means the first entry of that array, and
"empty" means the array is empty or missing, or the first entry's field is null or an empty string.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `attio`. |
| `external_id` | `id.record_id` | The record's `id.record_id`, or `None` when missing. |
| `full_name` | `values.name` | See *full_name derivation* below. |
| `primary_email` | `values.email_addresses` | See *primary_email* below. |
| `job_title` | `values.job_title` | The `value` of the first value, or `None` when empty. |
| `company_name` | — | Always `None`. Attio returns only a reference to the company, not its name. |
| `custom_fields` | selected attributes | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is `full_name` of the first `values.name` value when non-empty, with surrounding
   whitespace stripped.
2. Otherwise it is `first_name` and `last_name` of that value joined by a single space, each
   treated as empty when null, with surrounding whitespace stripped.
3. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email

- `primary_email` is `email_address` of the first `values.email_addresses` value, lowercased and
  trimmed.
- A missing or empty value maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` is a new dict with exactly these four keys, each `None` when its source is empty:
  - `company_record_id` — `target_record_id` of the first `values.company` value.
  - `phone_number` — `phone_number` of the first `values.phone_numbers` value.
  - `linkedin` — `value` of the first `values.linkedin` value.
  - `description` — `value` of the first `values.description` value.
- No other attribute is copied, and API metadata (`active_from`, `active_until`,
  `created_by_actor`, `attribute_type`) is never copied.

## Error contract

- The mapping does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by the mapping.
