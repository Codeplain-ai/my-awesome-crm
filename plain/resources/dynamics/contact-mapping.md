# Dynamics 365 contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the dynamics integration. The input
is a dict shaped like one entry of the `value[]` array returned by the Dataverse Web API query for
the `contact` entity (see the `ContactRecord` schema in `resources/dynamics/openapi.yaml`). The
output is an `IncomingContact` dict with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `dynamics`. |
| `external_id` | `contactid` | Required — raise `ValueError` if missing or empty. |
| `full_name` | `fullname`, else `firstname` + `lastname` | See *full_name derivation* below. |
| `primary_email` | `emailaddress1` | See *primary_email validation* below. |
| `phone` | `telephone1`, else `mobilephone` | `telephone1` when present and non-empty; otherwise `mobilephone`; otherwise `None`. |
| `job_title` | `jobtitle` | The `jobtitle` field, or `None` when missing or empty. |
| `company_name` | `parentcustomerid_account.name` | The `name` of the expanded parent account, or `None` when `parentcustomerid_account` is null, missing, or has no non-empty name. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `fullname` field when present and non-empty, with surrounding whitespace
   stripped.
2. Otherwise it is `firstname` and `lastname` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped.
3. Otherwise raise `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

## primary_email validation

- `primary_email` is the `emailaddress1` field, lowercased and trimmed, but only when it is a valid
  email address; otherwise `None`.
- A missing or empty `emailaddress1` maps to `None`.
- A non-empty `emailaddress1` that is not a valid email address also maps to `None` so the contact
  still maps; a warning is logged naming the contact's `contactid`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.

## custom_fields rules

- `custom_fields` captures every field on the input dict that is not consumed above and is not
  API metadata, copied verbatim into a new dict.
- Consumed keys are `contactid`, `fullname`, `firstname`, `lastname`, `emailaddress1`,
  `telephone1`, `mobilephone`, `jobtitle`, and `parentcustomerid_account`.
- API metadata is any key beginning with `@odata.` (for example `@odata.etag`) and any OData
  annotation key (one containing `@`, such as `...@OData.Community.Display.V1.FormattedValue` or
  `...@Microsoft.Dynamics.CRM.*`); these are never copied.
- The expanded `parentcustomerid_account` object is treated as consumed and is not copied into
  `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `contactid`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
