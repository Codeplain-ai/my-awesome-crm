# SugarCRM Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the SugarCRM integration. The input is
a dict shaped like one entry of the `records[]` array returned by the SugarCRM REST `GET /Contacts`
list endpoint (see the `ContactRecord` schema in `resources/sugarcrm/openapi.yaml`). The output is an
`IncomingContact` dict with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `sugarcrm`. |
| `external_id` | `id` | Required — raise `ValueError` if missing or empty. |
| `full_name` | `full_name` / `name`, else `first_name` + `last_name`, else the primary email | See *full_name derivation* below. |
| `primary_email` | the primary entry of the `email` array, else `email1` | See *primary_email validation* below. |
| `phone` | `phone_work`, else `phone_mobile` | `phone_work` when present and non-empty; otherwise `phone_mobile`; otherwise `None`. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | `account_name` | The flat `account_name` string, or `None` when missing or empty. |
| `custom_fields` | provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. `full_name` when present and non-empty, with surrounding whitespace stripped; otherwise `name`
   when present and non-empty, stripped.
2. Otherwise `first_name` and `last_name` joined by a single space, each treated as empty when null,
   with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise the selected primary email value, trimmed — used when non-empty.
4. Otherwise raise `ValueError`.

## primary_email selection

- The email is taken from the structured `email` array: the `email_address` of the entry whose
  `primary_address` is truthy; if no entry is marked primary, the `email_address` of the first entry
  that has a non-empty `email_address`.
- If the `email` array yields nothing usable, fall back to the flat `email1` field.
- This selected value then goes through *primary_email validation* below.

## primary_email validation

- `primary_email` is the selected email value, lowercased and trimmed, but only when it is a valid
  email address; otherwise `None`.
- A missing or empty selected email maps to `None`.
- A non-empty selected email that is not a valid email address also maps to `None` so the contact
  still maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.
- Note: when the selected email is used as the `full_name` fallback (a contact with no name) but is
  not a valid email address, `full_name` still takes the raw email string while `primary_email` is
  `None`.

## custom_fields rules

- `custom_fields` captures the Sugar provenance timestamps `date_entered` and `date_modified` from
  the input record, each copied verbatim when present and non-null.
- The consumed business keys (`id`, `first_name`, `last_name`, `name`, `full_name`, `email`,
  `email1`, `phone_work`, `phone_mobile`, `title`, `account_name`) are not copied into
  `custom_fields`.
- Sugar API metadata keys (any key beginning with `_`, such as `_acl` and `_module`) are never
  copied.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
