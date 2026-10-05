# HubSpot Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the HubSpot integration. The
input is a dict shaped like one entry of the `results[]` array returned by the HubSpot contacts
list API (see the `ContactRecord` schema in `resources/hubspot/openapi.yaml`). The output is a
contact `data` dict — the conventional contact shape the host stores verbatim under the `data`
of a `contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `hubspot`. |
| `external_id` | `id` | The record's `id`, or `None` when missing. |
| `full_name` | `properties.firstname`, `properties.lastname` | See *full_name derivation* below. |
| `primary_email` | `properties.email` | See *primary_email* below. |
| `job_title` | `properties.jobtitle` | The value, or `None` when missing or empty. |
| `company_name` | `properties.company` | The value (a plain string property), or `None` when missing or empty. |
| `custom_fields` | — | Always an empty dict. |

## full_name derivation

1. `full_name` is `firstname` and `lastname` joined by a single space, each treated as empty when
   null or missing, with surrounding whitespace stripped.
2. When both are empty it is an empty string. The mapping never raises for a missing name.

## primary_email

- `primary_email` is `email`, lowercased and trimmed.
- A missing or empty `email` maps to `None`.
- The value is passed through as-is otherwise; no email-format validity check is performed and no
  value is discarded.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict,
  including a record whose `properties` is missing or null.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
