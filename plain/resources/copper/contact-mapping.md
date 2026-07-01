# Copper People → contact-data mapping contract

The field-by-field contract for the pure mapping function of the Copper integration. The input is
a dict shaped like one entry of the JSON array returned by the Copper People search API (see the
`ContactRecord` schema in `resources/copper/openapi.yaml`). The output is a contact `data` dict —
the conventional contact shape the host stores verbatim under the `data` of a `contact` record. It
has exactly the keys listed below.

The host does **not** validate this dict: there is no deduplication, no merging, and no required
field. The mapping therefore maps best-effort and never raises for missing or malformed values —
it simply emits the keys below, using `None` (or an empty string for `full_name`) where a value is
absent.

## Field mapping rules

| Output key | Source | Rule |
|---|---|---|
| `provider_id` | — | Always the literal string `copper`. |
| `external_id` | `id` | The record's `id`, rendered as its decimal string form, or `None` when missing. |
| `full_name` | `name`, else `first_name` + `last_name` | See *full_name derivation* below. |
| `primary_email` | first/primary entry of `emails[]` | See *primary_email* below. |
| `job_title` | `title` | The `title` field, or `None` when missing or empty. |
| `company_name` | `company_name` | The flat `company_name` string, or `None` when missing or empty. |
| `custom_fields` | selected provenance fields | See *custom_fields rules* below. |

## external_id derivation

- `external_id` is the record `id`. Copper returns `id` as a number, so it is rendered as its
  decimal string form (for example the number `27140442` becomes the string `"27140442"`).
- A missing, null, or empty `id` maps to `None`. The mapping never raises for a missing id.

## full_name derivation

1. `full_name` is the `name` field when present and non-empty, with surrounding whitespace stripped.
2. Otherwise it is `first_name` and `last_name` joined by a single space, each treated as empty when
   null, with surrounding whitespace stripped.
3. Otherwise it is an empty string. The mapping never raises for a missing name.

## primary_email

- `primary_email` is taken from the first entry of `emails[]` whose `email` value is non-empty
  (the primary email), lowercased and trimmed.
- A missing or empty `emails[]` array, or one with no non-empty `email` value, maps to `None`.
- The value is passed through as-is otherwise; the host does not validate email format, so no
  validity check is performed and no value is discarded.

## custom_fields rules

- `custom_fields` captures the Copper provenance timestamps `date_created` and `date_modified`
  from the input record, each copied verbatim when present and non-null.
- The consumed business keys (`id`, `name`, `first_name`, `last_name`, `title`, `company_name`,
  `emails`) are not copied into `custom_fields`.
- The Copper `custom_fields` array (each `{custom_field_definition_id, value}` entry) is not copied
  verbatim, because its definition ids are opaque and not meaningful without a separate lookup.
- Record envelope and unused fields (`middle_name`, `prefix`, `suffix`, `company_id`, `assignee_id`,
  `contact_type_id`, `details`, `address`, `socials`, `websites`, `tags`, `date_last_contacted`,
  `interaction_count`) are not copied into `custom_fields`.

## Error contract

- The mapping function does not raise for record content — every input maps to an output dict.
- Errors that are not per-record mapping concerns (missing credentials, authentication failure,
  transport/HTTP errors) are raised by the `fetch(get_stored)` entry point, not by this function.
