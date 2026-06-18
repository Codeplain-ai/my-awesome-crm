# Nimble Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Nimble integration. The input is
a dict shaped like one entry of the `resources[]` array returned by the Nimble REST API contacts
list endpoint (see the `ContactRecord` schema in `resources/nimble/openapi.yaml`). Business data
lives under the record's `fields` map, where each field key (e.g. `first name`, `last name`,
`email`, `phone`, `title`, `company`) maps to an ARRAY of entry objects, each with a `value` (and
optional `modifier`/`group`/`label`). The output is an `IncomingContact` dict with exactly the keys
listed below.

## Reading a field value

For every field consumed below, the value is the `value` of the FIRST entry in that field's array.
A field is treated as **missing** (yielding `None` or an empty string before fallback) when its key
is absent, its array is empty, the first entry has no `value`, or that `value` is null or empty
after trimming. The integration never reads beyond the first entry of a field's array.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `nimble`. |
| `external_id` | `id` | Required — raise `ValueError` if missing or empty. |
| `full_name` | first value of `fields["first name"]` + first value of `fields["last name"]` | See *full_name derivation* below. |
| `primary_email` | first value of `fields["email"]` | See *primary_email validation* below. |
| `phone` | first value of `fields["phone"]` | The first `phone` entry value when present and non-empty; otherwise `None`. |
| `job_title` | first value of `fields["title"]` | The first `title` entry value, or `None` when missing or empty. |
| `company_name` | first value of `fields["company"]` | The first `company` entry value, or `None` when missing or empty. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. The first value of `fields["first name"]` and the first value of `fields["last name"]` joined by
   a single space, each treated as empty when missing or null, with surrounding whitespace stripped
   — used when that joined value is non-empty.
2. Otherwise the first value of `fields["email"]`, trimmed — used when non-empty. (Nimble contacts
   are commonly identified by email when no name is recorded.)
3. Otherwise the first value of `fields["company"]`, trimmed — used when non-empty.
4. Otherwise raise `ValueError`.

## primary_email validation

- `primary_email` is the first value of `fields["email"]`, lowercased and trimmed, but only when it
  is a valid email address; otherwise `None`.
- A missing or empty `email` maps to `None`.
- A non-empty `email` that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.
- Note: when `email` is used as the `full_name` fallback (a name-less contact) but is not a valid
  email address, `full_name` still takes the raw email string while `primary_email` is `None`.

## custom_fields rules

- `custom_fields` captures the record-level `record_type` value when present and non-null, copied
  verbatim under the key `record_type`, so the contact's Nimble kind is preserved.
- The consumed business field keys (`first name`, `last name`, `email`, `phone`, `title`,
  `company`) are not copied into `custom_fields`.
- The `fields` map itself and the record-level `id` are not copied into `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
