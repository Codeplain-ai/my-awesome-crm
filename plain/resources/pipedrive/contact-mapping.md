# Pipedrive Person → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Pipedrive integration. The input
is a dict shaped like one entry of the `data[]` array returned by the Pipedrive v1 `GET /v1/persons`
list API (see the `ContactRecord` schema in `resources/pipedrive/openapi.yaml`). The output is an
`IncomingContact` dict with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `pipedrive`. |
| `external_id` | `id` | Required — raise `ValueError` if missing or empty. Stringified from the numeric Pipedrive id. |
| `full_name` | `name`, else `first_name` + `last_name` | See *full_name derivation* below. |
| `primary_email` | primary entry of `email[]` | See *primary_email validation* below. |
| `phone` | primary entry of `phone[]` | See *phone derivation* below. |
| `job_title` | `job_title` | The `job_title` value, or `None` when missing or empty. |
| `company_name` | `org_name`, else `org_id.name` | The flat `org_name` string when non-empty; otherwise the `name` of the nested `org_id` object; otherwise `None`. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. `full_name` is the `name` field when present and non-empty, with surrounding whitespace stripped.
2. Otherwise it is `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise raise `ValueError`.

## primary_email validation

- `primary_email` is the chosen email value, lowercased and trimmed, but only when it is a valid
  email address; otherwise `None`.
- The chosen email value is the `value` of the `email[]` entry whose `primary` flag is true; if no
  entry is marked primary, it is the `value` of the first entry; if `email` is missing, null, or
  empty, the chosen email value is empty.
- A missing or empty chosen email value maps to `None`.
- A non-empty chosen email value that is not a valid email address also maps to `None` so the
  contact still maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.

## phone derivation

- `phone` is the `value` of the `phone[]` entry whose `primary` flag is true, when present and
  non-empty.
- Otherwise it is the `value` of the first `phone[]` entry, when present and non-empty.
- Otherwise `None` (including when `phone` is missing, null, or empty).
- The phone value is kept verbatim; no normalization is applied.

## custom_fields rules

- `custom_fields` captures every field on the input dict that is not consumed above and is not a
  record envelope field, copied verbatim into a new dict (for example provider-specific custom
  field keys Pipedrive returns).
- Consumed keys are `id`, `name`, `first_name`, `last_name`, `email`, `phone`, `job_title`,
  `org_id`, and `org_name`.
- These consumed keys are never copied into `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
