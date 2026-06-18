# Copper Contact → IncomingContact mapping contract

The field-by-field contract for the pure mapping function of the Copper integration. The input is
a dict shaped like one entry of the JSON array returned by the Copper People search API (see the
`ContactRecord` schema in `resources/copper/openapi.yaml`). The output is an `IncomingContact` dict
with exactly the keys listed below.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `copper`. |
| `external_id` | `id` | Required — raise `ValueError` if missing or empty. The Copper `id` is a number; convert it to its string form. |
| `full_name` | `name`, else `first_name` + `last_name` | See *full_name derivation* below. |
| `primary_email` | first/primary entry of `emails[]` | See *primary_email validation* below. |
| `phone` | first entry of `phone_numbers[]` | The `number` of the first `phone_numbers[]` entry that has a non-empty `number`; otherwise `None`. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | `company_name` | The flat `company_name` string, or `None` when missing or empty. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## external_id derivation

- `external_id` is the record `id`. Copper returns `id` as a number, so it is rendered as its
  decimal string form (for example the number `27140442` becomes the string `"27140442"`).
- A missing, null, or empty `id` raises `ValueError`.

## full_name derivation

`full_name` is derived by the first rule below that yields a non-empty value; if none do, the
function raises `ValueError`, because `IncomingContact` requires a non-empty `full_name`.

1. The `name` field, with surrounding whitespace stripped — used when that value is non-empty.
2. Otherwise `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped — used when that joined value is non-empty.
3. Otherwise raise `ValueError`.

## primary_email validation

- `primary_email` is taken from the first entry of `emails[]` whose `email` value is non-empty
  (the primary email), lowercased and trimmed, but only when it is a valid email address;
  otherwise `None`.
- A missing or empty `emails[]` array, or one with no non-empty `email` value, maps to `None`.
- A non-empty `email` that is not a valid email address also maps to `None` so the contact still
  maps; a warning is logged naming the contact's `id`. This is **not** a record-skip.
- Email validity is judged the same way the host judges it (the host's `email-validator` with
  deliverability / DNS checks disabled, matching the host's email-typed field), so any value
  emitted here is always accepted by the host's `IncomingContact` contract.

## custom_fields rules

- `custom_fields` captures the Copper provenance timestamps `date_created` and `date_modified`
  from the input record, each copied verbatim when present and non-null.
- The consumed business keys (`id`, `name`, `first_name`, `last_name`, `title`, `company_name`,
  `emails`, `phone_numbers`) are not copied into `custom_fields`.
- The Copper `custom_fields` array (each `{custom_field_definition_id, value}` entry) is not copied
  verbatim, because its definition ids are opaque and not meaningful without a separate lookup.
- Record envelope and unused fields (`middle_name`, `prefix`, `suffix`, `company_id`, `assignee_id`,
  `contact_type_id`, `details`, `address`, `socials`, `websites`, `tags`, `date_last_contacted`,
  `interaction_count`) are not copied into `custom_fields`.

## Error contract

- The function raises `ValueError` for exactly two conditions: a missing/empty `id`, or an
  underivable `full_name` (rules above). Everything else maps without raising.
- Callers (the integration's skip-and-log policy) treat a `ValueError` as "skip this one record".
