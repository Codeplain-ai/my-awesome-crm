# Streak Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Streak integration. The input is a
dict shaped like one entry of the plain JSON array returned by the Streak team contact list API (see
the `ContactRecord` schema in `resources/streak/openapi.yaml`). The output is an `IncomingContact`
dict with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `streak`. |
| `external_id` | `key` | Required — raise `ValueError` if missing or empty. |
| `full_name` | `fullName`, else `givenName` + `familyName`, else first `emailAddresses` entry | See *full_name derivation* below. |
| `primary_email` | `emailAddresses` | See *primary_email validation* below. |
| `phone` | `phoneNumbers` | The first non-empty entry of `phoneNumbers`; otherwise `None`. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | — | Always `None`. See *company_name* below. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. The `fullName` field, with surrounding whitespace stripped — used when present and non-empty.
2. Otherwise `givenName` and `familyName` joined by a single space, each treated as empty when null,
   with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise the first non-empty entry of the `emailAddresses` array, trimmed — used when present.
   (Streak requires every contact to have a name or at least one email address, so this fallback
   covers the email-only contacts.)
4. Otherwise raise `ValueError`.

## primary_email validation

- `primary_email` is the first non-empty entry of the `emailAddresses` array, lowercased and
  trimmed, but only when it is a valid email address; otherwise `None`.
- A missing or empty `emailAddresses` array maps to `None`.
- A non-empty email value that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `key`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.
- Note: when the first email is used as the `full_name` fallback (a name-less contact) but is not a
  valid email address, `full_name` still takes the raw email string while `primary_email` is `None`.

## company_name

- `company_name` is always `None`. Streak models organizations as separate objects linked to
  contacts; a Streak `ContactRecord` carries no reliable company string of its own, and the
  integration does not fetch the linked organization objects. If a future live cross-check shows a
  usable company field on the contact, map it here and update this contract.

## custom_fields rules

- `custom_fields` captures the Streak provenance timestamps `creationTimestamp` and
  `lastSavedTimestamp` from the input record, each copied verbatim when present and non-null.
- The consumed business keys (`key`, `fullName`, `givenName`, `familyName`, `emailAddresses`,
  `phoneNumbers`, `title`) are not copied into `custom_fields`.
- `teamKey`, `lastUpdatedTimestamp`, `other`, the social handles, `addresses`, and `photoUrl` are
  not copied into `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `key`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
