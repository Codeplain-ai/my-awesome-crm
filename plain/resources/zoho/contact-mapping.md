# Zoho CRM Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Zoho integration. The input is a
dict shaped like one entry of the `data[]` array returned by the Zoho CRM v3 Get Records API for the
`Contacts` module (see the `ContactRecord` schema in `resources/zoho/openapi.yaml`). The output is an
`IncomingContact` dict with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `zoho`. |
| `external_id` | `id` | Required — raise `ValueError` if missing or empty. |
| `full_name` | `Full_Name`, else `First_Name` + `Last_Name`, else `Email` | See *full_name derivation* below. |
| `primary_email` | `Email` | See *primary_email validation* below. |
| `phone` | `Phone`, else `Mobile` | `Phone` when present and non-empty; otherwise `Mobile`; otherwise `None`. |
| `job_title` | `Title` | The `Title` value, or `None` when missing or empty. |
| `company_name` | `Account_Name` | See *company_name derivation* below. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. The `Full_Name` field when present and non-empty, with surrounding whitespace stripped.
2. Otherwise `First_Name` and `Last_Name` joined by a single space, each treated as empty when null,
   with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise the `Email` value, trimmed — used when non-empty.
4. Otherwise raise `ValueError`.

## company_name derivation

`Account_Name` is a lookup field that the API returns in one of three shapes. `company_name` is
derived as follows:

1. When `Account_Name` is an object, `company_name` is its `name` value, trimmed — or `None` when
   `name` is missing, null, or empty.
2. When `Account_Name` is a plain string, `company_name` is that string, trimmed — or `None` when
   empty.
3. When `Account_Name` is null or missing, `company_name` is `None`.

## primary_email validation

- `primary_email` is the `Email` field, lowercased and trimmed, but only when it is a valid email
  address; otherwise `None`.
- A missing or empty `Email` maps to `None`.
- A non-empty `Email` that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.
- Note: when `Email` is used as the `full_name` fallback but is not a valid email address,
  `full_name` still takes the raw email string while `primary_email` is `None`.

## custom_fields rules

- `custom_fields` captures every field on the input dict that is not consumed above and is not Zoho
  system metadata, copied verbatim into a new dict (for example any extra business field returned in
  the record).
- Consumed keys are `id`, `Full_Name`, `First_Name`, `Last_Name`, `Email`, `Phone`, `Mobile`,
  `Title`, and `Account_Name`.
- The `Account_Name` lookup (in any of its shapes — object, string, or null) is treated as consumed
  and is not copied into `custom_fields`.
- Zoho system metadata is never copied into `custom_fields`: any key whose name starts with `$`
  (for example `$approved`, `$editable`, `$currency_symbol`, `$field_states`) and the `Owner`
  lookup object are excluded.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
