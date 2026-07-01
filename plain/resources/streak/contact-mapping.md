# Streak Contact → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Streak integration. The input is a
dict shaped like one entry of the plain JSON array returned by the Streak team contact list API (see
the `ContactRecord` schema in `resources/streak/openapi.yaml`). The output is a contact `data` dict —
the conventional contact shape the host stores verbatim under the `data` of a `contact` record. It
has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `streak`. |
| `external_id` | `key` | The record's `key`, or `None` when missing. |
| `full_name` | `fullName`, else `givenName` + `familyName`, else first `emailAddresses` entry | See *full_name derivation* below. |
| `primary_email` | `emailAddresses` | See *primary_email* below. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | — | Always `None`. See *company_name* below. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

1. `full_name` is the `fullName` field when present and non-empty, with surrounding whitespace
   stripped.
2. Otherwise it is `givenName` and `familyName` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise it is the first non-empty entry of the `emailAddresses` array, trimmed — used when
   present. (Streak requires every contact to have a name or at least one email address, so this
   fallback covers the email-only contacts.)
4. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email

- `primary_email` is the first non-empty entry of the `emailAddresses` array, lowercased and trimmed.
- A missing or empty `emailAddresses` array maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## company_name

- `company_name` is always `None`. Streak models organizations as separate objects linked to
  contacts; a Streak `ContactRecord` carries no reliable company string of its own, and the
  integration does not fetch the linked organization objects. If a future live cross-check shows a
  usable company field on the contact, map it here and update this contract.

## custom_fields rules

- `custom_fields` captures the Streak provenance timestamps `creationTimestamp` and
  `lastSavedTimestamp` from the input record, each copied verbatim when present and non-null.
- The consumed business keys (`key`, `fullName`, `givenName`, `familyName`, `emailAddresses`,
  `title`) are not copied into `custom_fields`.
- `teamKey`, `lastUpdatedTimestamp`, `other`, the social handles, `addresses`, and `photoUrl` are
  not copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
