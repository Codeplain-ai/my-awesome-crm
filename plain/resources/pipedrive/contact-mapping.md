# Pipedrive Person → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Pipedrive integration. The input
is a dict shaped like one entry of the `data[]` array returned by the Pipedrive v1 `GET /v1/persons`
list API (see the `ContactRecord` schema in `resources/pipedrive/openapi.yaml`). The output is a
contact `data` dict — the conventional contact shape the host stores verbatim under the `data` of a
`contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `pipedrive`. |
| `external_id` | `id` | The record's `id` stringified, or `None` when missing. |
| `full_name` | `name`, else `first_name` + `last_name` | See *full_name derivation* below. |
| `primary_email` | primary entry of `email[]` | See *primary_email* below. |
| `job_title` | `job_title` | The `job_title` value, or `None` when missing or empty. |
| `company_name` | `org_name`, else `org_id.name` | The flat `org_name` string when non-empty; otherwise the `name` of the nested `org_id` object; otherwise `None`. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `name` field when present and non-empty, with surrounding whitespace stripped.
2. Otherwise it is `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped.
3. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email

- The chosen email value is the `value` of the `email[]` entry whose `primary` flag is true; if no
  entry is marked primary, it is the `value` of the first entry; if `email` is missing, null, or
  empty, the chosen email value is empty.
- `primary_email` is that chosen email value, lowercased and trimmed.
- A missing or empty chosen email value maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` captures every field on the input dict that is not consumed above and is not a
  record envelope field, copied verbatim into a new dict (for example provider-specific custom
  field keys Pipedrive returns).
- Consumed keys are `id`, `name`, `first_name`, `last_name`, `email`, `job_title`, `org_id`, and
  `org_name`.
- The `phone` field that Pipedrive returns on every person is explicitly discarded and is never
  copied into `custom_fields`; the integration stores no phone data.
- These consumed keys and the discarded `phone` field are never copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
