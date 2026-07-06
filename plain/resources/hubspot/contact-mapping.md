# HubSpot Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the HubSpot integration. The input is
a dict shaped like one entry of the `results[]` array returned by the HubSpot CRM v3 list-contacts
API (see the `ContactRecord` schema in `resources/hubspot/openapi.yaml`). The output is a contact
`data` dict — the conventional contact shape the host stores verbatim under the `data` of a
`contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values — it
simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

Note: HubSpot returns business fields inside a nested `properties` object, not at the top level.
Every source field below is read from the record's `properties` object, except `external_id` which
comes from the top-level `id`.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `hubspot`. |
| `external_id` | top-level `id` | The record's `id`, or `None` when missing. |
| `full_name` | `properties.firstname` + `properties.lastname` | See *full_name derivation* below. |
| `primary_email` | `properties.email` | See *primary_email* below. |
| `job_title` | `properties.jobtitle` | The `jobtitle` property, or `None` when missing or empty. |
| `company_name` | `properties.company` | The `company` property, or `None` when missing or empty. |
| `custom_fields` | remaining properties | See *custom_fields rules* below. |

## full_name derivation

HubSpot has no single compound name field, so `full_name` is always derived from the first and last
name.

1. `full_name` is `properties.firstname` and `properties.lastname` joined by a single space, each
   treated as empty when null or missing, with surrounding whitespace stripped.
2. When both are absent or empty the result is an empty string. The mapping never raises for a
   missing name.

## primary_email

- `primary_email` is `properties.email`, lowercased and trimmed.
- A missing or empty `email` maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` captures every entry of the input record's `properties` object that is not
  consumed above, copied verbatim into a new dict (for example `createdate`, `lastmodifieddate`).
- Consumed property keys are `firstname`, `lastname`, `email`, `jobtitle`, and `company`.
- `hs_object_id` is a duplicate of the top-level `id`; it is treated as consumed and is not copied
  into `custom_fields`.
- Top-level record metadata (`id`, `createdAt`, `updatedAt`, `archived`, `url`, and the `properties`
  wrapper itself) is never copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
