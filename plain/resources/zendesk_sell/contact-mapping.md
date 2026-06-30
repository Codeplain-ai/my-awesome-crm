# Zendesk Sell Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Zendesk Sell integration. The
input is a dict shaped like the unwrapped `data` object of one entry of the `items[]` array
returned by the Zendesk Sell `GET /v2/contacts` API (see the `ContactRecord` schema in
`resources/zendesk_sell/openapi.yaml`). The business contact lives under each item's `data` object,
never at the item top level; the caller unwraps `data` before invoking this function. The output is
a contact `data` dict — the conventional contact shape the host stores verbatim under the `data` of
a `contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `zendesk_sell`. |
| `external_id` | `id` | The contact id rendered as a string, or `None` when missing or empty. |
| `full_name` | depends on `is_organization` | See *full_name derivation* below. |
| `primary_email` | `email` | See *primary_email* below. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | `organization_name` | The `organization_name` value, or `None` when missing or empty. |
| `custom_fields` | provenance + custom fields | See *custom_fields rules* below. |

## external_id derivation

- `external_id` is the `id` value rendered as a string (the Sell id is numeric).
- A missing, null, or empty `id` maps to `None`. The mapping never raises for a missing id.

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, it is an
empty string. The mapping never raises for a missing name.

1. When `is_organization` is true, the `name` value, with surrounding whitespace stripped — used
   when non-empty. (An organization's display name lives in `name`.)
2. Otherwise `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty. (A
   person's name lives in first_name / last_name.)
3. Otherwise the `name` value, with surrounding whitespace stripped — used when non-empty (covers a
   person record that carries only a populated `name`).
4. Otherwise the `email` value, trimmed — used when non-empty.
5. Otherwise an empty string.

## primary_email

- `primary_email` is the `email` field, lowercased and trimmed.
- A missing or empty `email` maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.
- Note: when `email` is used as the `full_name` fallback, `full_name` takes the raw email string
  while `primary_email` is the same email lowercased and trimmed.

## company_name

- `company_name` is the `organization_name` value, trimmed, or `None` when missing or empty.
- Sell does not denormalize `organization_name` onto every record, so `company_name` is frequently
  `None`; the integration performs no second lookup to resolve a linked organization's name.

## custom_fields rules

- `custom_fields` starts from the contents of the input `custom_fields` map, each key copied
  verbatim when present and non-null.
- The Sell provenance fields `created_at`, `updated_at`, `contact_id`, `parent_organization_id`,
  and `is_organization` are added when present and non-null, so provenance is not lost.
- The consumed business keys (`id`, `name`, `first_name`, `last_name`, `email`, `phone`,
  `mobile`, `title`, `organization_name`) are not copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
