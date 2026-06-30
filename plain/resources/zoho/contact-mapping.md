# Zoho CRM Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Zoho integration. The input is a
dict shaped like one entry of the `data[]` array returned by the Zoho CRM v3 Get Records API for the
`Contacts` module (see the `ContactRecord` schema in `resources/zoho/openapi.yaml`). The output is a
contact `data` dict — the conventional contact shape the host stores verbatim under the `data` of a
`contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `zoho`. |
| `external_id` | `id` | The record's `id`, or `None` when missing. |
| `full_name` | `Full_Name`, else `First_Name` + `Last_Name`, else `Email` | See *full_name derivation* below. |
| `primary_email` | `Email` | See *primary_email* below. |
| `job_title` | `Title` | The `Title` value, or `None` when missing or empty. |
| `company_name` | `Account_Name` | See *company_name derivation* below. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `Full_Name` field when present and non-empty, with surrounding whitespace
   stripped.
2. Otherwise it is `First_Name` and `Last_Name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise it is the `Email` value, trimmed — used when non-empty.
4. Otherwise it is an empty string. The mapping never raises for a missing name.

## company_name derivation

`Account_Name` is a lookup field that the API returns in one of three shapes. `company_name` is
derived as follows:

1. When `Account_Name` is an object, `company_name` is its `name` value, trimmed — or `None` when
   `name` is missing, null, or empty.
2. When `Account_Name` is a plain string, `company_name` is that string, trimmed — or `None` when
   empty.
3. When `Account_Name` is null or missing, `company_name` is `None`.

## primary_email

- `primary_email` is the `Email` field, lowercased and trimmed.
- A missing or empty `Email` maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

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

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
