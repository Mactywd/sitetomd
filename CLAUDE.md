# Directus Onboarding Generator

Generate Directus-ready collection snapshots and data schemas from scraped website content and internal property documents.

## Directory structure

```
website/exported.md     ← full website scraped as markdown (run website/main.py)
information/            ← internal docs: PDFs, DOCX, QnA files, pricing, wifi passwords, etc.
```

Output files to produce (in `output/` directory, create it if missing):
- `output/schema.json` — extracted structured data
- `output/snapshot_input.json` — minimal field descriptor (written by the LLM)
- `output/snapshot.json` — full Directus snapshot (compiled by `to_snapshot.py`)

**Do not write `output/snapshot.json` by hand.** Write `output/snapshot_input.json` instead, then run:
```
python to_snapshot.py
```

## Fixed 4-collection model

Every property uses exactly these collections, where `{name}` is the lowercase snake_case property identifier (e.g. `chiusella`, `villa_rossi`) and `{units}` is either `apartments` or `rooms` (see rule below):

| Collection | Type | Group | Sort |
|---|---|---|---|
| `{name}` | singleton | none | 1 |
| `{name}_{units}` | list | `{name}` | 1 |
| `{name}_experiences` | list | `{name}` | 2 |
| `{name}_services` | list | `{name}` | 3 |

**apartments vs rooms:** inspect the website content to decide.
- Use `rooms` when the property sells individual rooms that share common areas (B&B, hotel, hostel, agriturismo with shared kitchen, etc.).
- Use `apartments` when the property sells self-contained units with their own facilities (holiday apartments, villas, agriturismo with independent units, etc.).
- When in doubt, prefer `rooms` for accommodation-focused properties and `apartments` for rental-focused ones.

## Field naming conventions

- All field names: `snake_case`
- Prefix fields with their entity type: `apartment_*` (or `room_*`), `experience_*`, `service_*`
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

(Use `"rooms"` instead of `"apartments"` as the key when appropriate.)

## snapshot_input.json format

This is the minimal input for `to_snapshot.py`. It compiles into the full `output/snapshot.json`.

```json
{
  "name": "{name}",
  "unit_collection": "apartments",
  "property": [
    {"field": "property_name", "type": "string"},
    {"field": "property_description", "type": "text"}
  ],
  "units": [
    {"field": "apartment_name", "type": "string"},
    {"field": "apartment_has_wifi", "type": "boolean"},
    {"field": "apartment_kitchen_type", "type": "string",
     "interface": "select-dropdown",
     "choices": ["Kitchenette", "Full kitchen", "None"]}
  ],
  "experiences": [
    {"field": "experience_name", "type": "string"}
  ],
  "services": [
    {"field": "service_name", "type": "string"}
  ]
}
```

Rules for `snapshot_input.json`:
- `id` is added automatically to every collection — do not include it.
- `additional_info` is added automatically at the end of every child collection — do not include it.
- Per-field keys: `field` (required), `type` (required), `interface` (optional override), `choices` (optional, for dropdowns).
- Valid types: `string`, `text`, `integer`, `float`, `boolean`, `datetime`, `json`, `image`, `file`.
- For a `select-dropdown`, add `"interface": "select-dropdown"` and `"choices": [...]`.
- For a `select-multiple-dropdown`, use `"type": "json"`, `"interface": "select-multiple-dropdown"`, and `"choices": [...]`.

## Generation order

1. Generate `output/schema.json` first (structured property data).
2. Generate `output/snapshot_input.json` (minimal field descriptor — ~50–80 lines).
3. Run `python to_snapshot.py` to compile `output/snapshot.json`.

The schema tells you which fields exist; `snapshot_input.json` is the mechanical description of those fields; `to_snapshot.py` handles all Directus boilerplate.
