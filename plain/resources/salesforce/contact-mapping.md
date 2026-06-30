# Salesforce Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Salesforce integration. The
input is a dict shaped like one entry of the `records[]` array returned by the Salesforce REST
query API for the `Contact` object (see the `ContactRecord` schema in
`resources/salesforce/openapi.yaml`). The output is a contact `data` dict — the conventional
contact shape the host stores verbatim under the `data` of a `contact` record. It has exactly the
keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `salesforce`. |
| `external_id` | `Id` | The record's `Id`, or `None` when missing. |
| `full_name` | `Name`, else `FirstName` + `LastName` | See *full_name derivation* below. |
| `primary_email` | `Email` | See *primary_email* below. |
| `job_title` | `Title` | The `Title` field, or `None` when missing or empty. |
| `company_name` | `Account.Name` | The `Name` value of the nested `Account` object, or `None` when `Account` is null, missing, or has no non-empty name. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `Name` field when present and non-empty, with surrounding whitespace stripped.
2. Otherwise it is `FirstName` and `LastName` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped.
3. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email

- `primary_email` is the `Email` field, lowercased and trimmed.
- A missing or empty `Email` maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` captures every field on the input dict that is not consumed above and is not
  API metadata, copied verbatim into a new dict (for example `Department`).
- Consumed keys are `Id`, `Name`, `FirstName`, `LastName`, `Email`, `Phone`, `MobilePhone`,
  `Title`, and `Account`.
- API metadata is the `attributes` key on the record (and any nested `attributes` object); these
  are never copied.
- The nested `Account` object is treated as consumed and is not copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
