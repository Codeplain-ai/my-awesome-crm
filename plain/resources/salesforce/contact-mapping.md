# Salesforce Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Salesforce integration. The
input is a dict shaped like one entry of the `records[]` array returned by the Salesforce REST
query API for the `Contact` object (see the `ContactRecord` schema in
`resources/salesforce/openapi.yaml`). The output is an `IncomingContact` dict with exactly the
keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `salesforce`. |
| `external_id` | `Id` | Required — raise `ValueError` if missing or empty. |
| `full_name` | `Name`, else `FirstName` + `LastName` | See *full_name derivation* below. |
| `primary_email` | `Email` | See *primary_email validation* below. |
| `phone` | `Phone`, else `MobilePhone` | `Phone` when present and non-empty; otherwise `MobilePhone`; otherwise `None`. |
| `job_title` | `Title` | The `Title` field, or `None` when missing or empty. |
| `company_name` | `Account.Name` | The `Name` value of the nested `Account` object, or `None` when `Account` is null, missing, or has no non-empty name. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `Name` field when present and non-empty, with surrounding whitespace stripped.
2. Otherwise it is `FirstName` and `LastName` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped.
3. Otherwise raise `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

## primary_email validation

- `primary_email` is the `Email` field, lowercased and trimmed, but only when it is a valid email
  address; otherwise `None`.
- A missing or empty `Email` maps to `None`.
- A non-empty `Email` that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `Id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.

## custom_fields rules

- `custom_fields` captures every field on the input dict that is not consumed above and is not
  API metadata, copied verbatim into a new dict (for example `Department`).
- Consumed keys are `Id`, `Name`, `FirstName`, `LastName`, `Email`, `Phone`, `MobilePhone`,
  `Title`, and `Account`.
- API metadata is the `attributes` key on the record (and any nested `attributes` object); these
  are never copied.
- The nested `Account` object is treated as consumed and is not copied into `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `Id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
