# Zendesk Sell Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Zendesk Sell integration. The
input is a dict shaped like the unwrapped `data` object of one entry of the `items[]` array
returned by the Zendesk Sell `GET /v2/contacts` API (see the `ContactRecord` schema in
`resources/zendesk_sell/openapi.yaml`). The business contact lives under each item's `data` object,
never at the item top level; the caller unwraps `data` before invoking this function. The output is
an `IncomingContact` dict with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `zendesk_sell`. |
| `external_id` | `id` | Required — the contact id as a string. Raise `ValueError` if missing or empty. |
| `full_name` | depends on `is_organization` | See *full_name derivation* below. |
| `primary_email` | `email` | See *primary_email validation* below. |
| `phone` | `phone`, else `mobile` | `phone` when present and non-empty; otherwise `mobile`; otherwise `None`. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | `organization_name` | The `organization_name` value, or `None` when missing or empty. |
| `custom_fields` | provenance + custom fields | See *custom_fields rules* below. |

## external_id derivation

- `external_id` is the `id` value rendered as a string (the Sell id is numeric).
- A missing, null, or empty `id` raises `ValueError`, because `IncomingContact` requires a
  non-empty `external_id`.

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. When `is_organization` is true, the `name` value, with surrounding whitespace stripped — used
   when non-empty. (An organization's display name lives in `name`.)
2. Otherwise `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty. (A
   person's name lives in first_name / last_name.)
3. Otherwise the `name` value, with surrounding whitespace stripped — used when non-empty (covers a
   person record that carries only a populated `name`).
4. Otherwise the `email` value, trimmed — used when non-empty.
5. Otherwise raise `ValueError`.

## primary_email validation

- `primary_email` is the `email` field, lowercased and trimmed, but only when it is a valid email
  address; otherwise `None`.
- A missing or empty `email` maps to `None`.
- A non-empty `email` that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.
- Note: when `email` is used as the `full_name` fallback but is not a valid email address,
  `full_name` still takes the raw email string while `primary_email` is `None`.

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

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
