# Dynamics 365 contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the dynamics integration. The input
is a dict shaped like one entry of the `value[]` array returned by the Dataverse Web API query for
the `contact` entity (see the `ContactRecord` schema in `resources/dynamics/openapi.yaml`). The
output is a contact `data` dict — the conventional contact shape the host stores verbatim under the
`data` of a `contact` record. It has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `dynamics`. |
| `external_id` | `contactid` | The record's `contactid`, or `None` when missing. |
| `full_name` | `fullname`, else `firstname` + `lastname` | See *full_name derivation* below. |
| `primary_email` | `emailaddress1` | See *primary_email* below. |
| `job_title` | `jobtitle` | The `jobtitle` field, or `None` when missing or empty. |
| `company_name` | `parentcustomerid_account.name` | The `name` of the expanded parent account, or `None` when `parentcustomerid_account` is null, missing, or has no non-empty name. |
| `custom_fields` | all remaining fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `fullname` field when present and non-empty, with surrounding whitespace
   stripped.
2. Otherwise it is `firstname` and `lastname` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped.
3. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email

- `primary_email` is the `emailaddress1` field, lowercased and trimmed.
- A missing or empty `emailaddress1` maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

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

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
