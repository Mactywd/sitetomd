# Directus Onboarding Generator

Generate Directus-ready collection snapshots and data schemas from scraped website content and internal property documents.

## Directory structure

```
website/exported.md     ← full website scraped as markdown (run website/main.py)
information/            ← internal docs: PDFs, DOCX, QnA files, pricing, wifi passwords, etc.
examples/snapshot_eg.json  ← reference: Directus snapshot format
examples/schema_eg.json    ← reference: data schema format
```

Output files to produce (in `output/` directory, create it if missing):
- `output/schema.json` — extracted structured data
- `output/snapshot.json` — Directus collection + field definitions

## Fixed 4-collection model

Every property uses exactly these collections, where `{name}` is the lowercase snake_case property identifier (e.g. `chiusella`, `villa_rossi`):

| Collection | Type | Group | Sort |
|---|---|---|---|
| `{name}` | singleton | none | 1 |
| `{name}_apartments` | list | `{name}` | 1 |
| `{name}_experiences` | list | `{name}` | 2 |
| `{name}_services` | list | `{name}` | 3 |

## Field naming conventions

- All field names: `snake_case`
- Prefix fields with their entity type: `apartment_*`, `experience_*`, `service_*`
- Main singleton fields: `property_*`
- Every collection includes `id` (uuid, hidden, readonly) as field sort 1
- Always include `additional_info` (text, nullable) as the last field in child collections

## Directus field type mapping

| Value type | Directus `type` | `data_type` | `interface` | `special` | `max_length` |
|---|---|---|---|---|---|
| UUID / primary key | `uuid` | `uuid` | `input` | `["uuid"]` | null |
| Short text (≤255 chars) | `string` | `character varying` | `input` | null | 255 |
| Long text / descriptions | `text` | `text` | `input-rich-text-html` | null | null |
| Integer | `integer` | `integer` | `input` | null | null |
| Float / decimal | `float` | `real` | `input` | null | null |
| Boolean | `boolean` | `boolean` | `boolean` | `["cast-boolean"]` | null |
| Date / time | `dateTime` | `timestamp with time zone` | `datetime` | `["date-created"]` or null | null |
| Enum / category (single) | `string` | `character varying` | `select-dropdown` | null | 255 |
| Tags / multi-value list | `json` | `jsonb` | `tags` | `["cast-json"]` | null |
| Object / nested data | `json` | `jsonb` | `input-code` | `["cast-json"]` | null |
| Image (single) | `uuid` | `uuid` | `file-image` | `["file"]` | null |
| File (single) | `uuid` | `uuid` | `file` | `["file"]` | null |

**Rules:**
- `id` field: `hidden: true`, `readonly: true`, `is_nullable: false`, `is_unique: true`, `is_primary_key: true`
- All other fields: `hidden: false`, `readonly: false`, `is_nullable: true`, `is_unique: false`, `is_primary_key: false`
- `numeric_precision` and `numeric_scale`: `null` for all types except integer (32 and 0 respectively)
- `has_auto_increment`: always `false`
- `foreign_key_table` / `foreign_key_column`: always `null`

## Interface selection guide

Choose the interface based on what makes most sense for an editor using the Directus admin UI.

### Text & Numbers

| Interface | `interface` value | When to use |
|---|---|---|
| Input | `input` | Default for short text, numbers, URLs, UUIDs. Any single-line value. |
| Textarea | `textarea` | Plain multiline text where formatting is not needed (notes, internal memos). |
| WYSIWYG | `input-rich-text-html` | Long descriptive text that may need formatting: descriptions, histories, location overviews. Use `type: "text"`. |
| Markdown | `input-rich-text-md` | Same as WYSIWYG but preferred when content will be rendered via markdown pipeline. |
| Code | `input-code` | Raw JSON objects, structured data, embedded config. Pair with `type: "json"`. |
| Slider | `slider` | Numeric values with a known min/max range (e.g. star rating 1–5, occupancy 1–20). |

### Selection

| Interface | `interface` value | When to use |
|---|---|---|
| Toggle | `boolean` | Any true/false flag (has_wifi, is_shared, is_included, crib_available). |
| Dropdown | `select-dropdown` | Single value from a fixed set of options (category, type, floor, kitchen_type). Pair with `type: "string"`. |
| Multiple Dropdown | `select-multiple-dropdown` | Multiple values from a fixed set. Pair with `type: "json"`, `special: ["cast-json"]`. |
| Tags | `tags` | Free-form list of values without a fixed enum (amenities, keywords, labels). Pair with `type: "json"`. |
| Datetime | `datetime` | Date, time, or datetime fields (check-in, check-out, created_at). Pair with `type: "dateTime"`. |
| Color | `color` | Hex color values. Pair with `type: "string"`. |

### Relational / Media

| Interface | `interface` value | When to use |
|---|---|---|
| Image | `file-image` | Single image reference. Pair with `type: "uuid"`, `special: ["file"]`. |
| File | `file` | Single file reference (PDF, document). Pair with `type: "uuid"`, `special: ["file"]`. |
| Many to One | `many-to-one` | Single related item from another collection (e.g. a category record). |
| One to Many | `one-to-many` | List of child items belonging to this record. |

### Presentation (no data stored)

| Interface | `interface` value | When to use |
|---|---|---|
| Divider | `presentation-divider` | Visual separator between logical field groups in the editor form. |
| Notice | `presentation-notice` | Display a help note or warning in the editor (e.g. "Fill in all fields before publishing"). |

## Snapshot envelope

```json
{
  "data": {
    "version": 1,
    "directus": "11.15.4",
    "vendor": "postgres",
    "collections": [...],
    "fields": [...],
    "relations": []
  }
}
```

## Schema format

```json
[
  { "apartments": [ { ...apartment fields... } ] },
  { "experiences": [ { ...experience fields... } ] },
  { "services": [ { ...service fields... } ] },
  { "{name}": [ { ...property fields... } ] }
]
```

## Generation order

Always generate **schema first**, then derive the snapshot from it. The schema tells you which fields exist and what types they are; the snapshot is the mechanical translation of those fields into Directus format.
