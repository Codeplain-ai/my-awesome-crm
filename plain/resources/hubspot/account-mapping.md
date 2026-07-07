# HubSpot Company → account-data mapping contract

The field-by-field contract for the pure mapping function that converts one HubSpot Company into an
account `data` dict. The input is a dict shaped like one entry of the `results[]` array returned by
the HubSpot CRM v3 companies API (see the `CompanyRecord` schema in `resources/hubspot/openapi.yaml`).
The output is an account `data` dict — the conventional account shape the host stores verbatim under
the `data` of an `account` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping maps best-effort and never raises for missing or malformed values — it simply
emits the keys below, using `None` where a value is absent.

Note: HubSpot returns business fields inside a nested `properties` object, not at the top level.
Every source field below is read from the record's `properties` object, except `external_id` which
comes from the top-level `id`.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `hubspot`. |
| `external_id` | top-level `id` | The record's `id`, or `None` when missing. |
| `name` | `properties.name` | The company name, trimmed; `None` when missing or empty. |
| `domain` | `properties.domain` | The company domain, lowercased and trimmed; `None` when missing or empty. |
| `industry` | `properties.industry` | The industry value; `None` when missing or empty. |
| `custom_fields` | remaining properties | See *custom_fields rules* below. |

## name

- `name` is `properties.name` with surrounding whitespace stripped.
- A missing or empty `name` maps to `None`. The mapping never raises for a missing name.

## domain

- `domain` is `properties.domain`, lowercased and trimmed.
- A missing or empty `domain` maps to `None`. The value is passed through as-is otherwise; no
  format validation is performed.

## custom_fields rules

- `custom_fields` captures every entry of the input record's `properties` object that is not
  consumed above, copied verbatim into a new dict (for example `createdate`, `hs_lastmodifieddate`,
  `city`, `country`, `phone`).
- Consumed property keys are `name`, `domain`, and `industry`.
- `hs_object_id` is a duplicate of the top-level `id`; it is treated as consumed and is not copied
  into `custom_fields`.
- Top-level record metadata (`id`, `createdAt`, `updatedAt`, `archived`, `url`, and the `properties`
  wrapper itself) is never copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
