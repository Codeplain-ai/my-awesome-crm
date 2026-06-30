# SugarCRM Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the SugarCRM integration. The input
is a dict shaped like one entry of the `records[]` array returned by the SugarCRM REST
`GET /Contacts` list endpoint (see the `ContactRecord` schema in
`resources/sugarcrm/openapi.yaml`). The output is a contact `data` dict — the conventional contact
shape the host stores verbatim under the `data` of a `contact` record. It has exactly the keys
listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `sugarcrm`. |
| `external_id` | `id` | The record's `id`, or `None` when missing. |
| `full_name` | `full_name` / `name`, else `first_name` + `last_name`, else the primary email | See *full_name derivation* below. |
| `primary_email` | the primary entry of the `email` array, else `email1` | See *primary_email* below. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | `account_name` | The flat `account_name` string, or `None` when missing or empty. |
| `custom_fields` | provenance fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `full_name` field when present and non-empty, with surrounding whitespace
   stripped; otherwise `name` when present and non-empty, stripped.
2. Otherwise it is `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise it is the selected primary email value, trimmed — used when non-empty.
4. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email selection

- The email is taken from the structured `email` array: the `email_address` of the entry whose
  `primary_address` is truthy; if no entry is marked primary, the `email_address` of the first entry
  that has a non-empty `email_address`.
- If the `email` array yields nothing usable, fall back to the flat `email1` field.

## primary_email

- `primary_email` is the selected email value, lowercased and trimmed.
- A missing or empty selected email maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` captures the Sugar provenance timestamps `date_entered` and `date_modified` from
  the input record, each copied verbatim when present and non-null.
- The consumed business keys (`id`, `first_name`, `last_name`, `name`, `full_name`, `email`,
  `email1`, `phone_work`, `phone_mobile`, `title`, `account_name`) are not copied into
  `custom_fields`.
- Sugar API metadata keys (any key beginning with `_`, such as `_acl` and `_module`) are never
  copied.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
