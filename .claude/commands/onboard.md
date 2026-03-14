Generate the Directus schema and snapshot for a new property onboarding.

## Step 1 — Identify the property name

Ask the user for the property identifier if not already given (e.g. `villa_rossi`). This will be used as `{name}` throughout. It must be lowercase snake_case.

## Step 2 — Read all sources

Read every available source file:
- `website/exported.md` — full scraped website content
- Every file inside `information/` — internal documents (PDFs, DOCX, QnA, pricing, etc.)

If `website/exported.md` does not exist, warn the user and ask them to run `website/main.py` first.

## Step 3 — Generate schema.json

Analyze all source content and extract structured data. Produce `output/schema.json` (create the `output/` directory if it doesn't exist).

Rules:
- Extract every distinct apartment, experience, and service mentioned across all sources
- Merge information from multiple sources (website + internal docs) — internal docs take priority for accuracy
- Field names must be `snake_case`, prefixed with entity type (`apartment_*`, `experience_*`, `service_*`, `property_*`)
- Use `null` for missing values, never omit a field that exists on other items in the same collection
- The main singleton object (`{name}`) captures property-level info: name, type, description, location, directions, distances, etc.
- `additional_info` should consolidate any notable details not captured by other fields
- All items in the same collection must have identical field sets (no sparse fields)
- Refer to `examples/schema_eg.json` for the expected format and field granularity

Output format:
```json
[
  { "apartments": [ ... ] },
  { "experiences": [ ... ] },
  { "services": [ ... ] },
  { "{name}": [ ... ] }
]
```

## Step 4 — Generate snapshot.json

Derive the Directus snapshot from `output/schema.json`. Produce `output/snapshot.json`.

Rules:
- Use exactly the 4-collection structure defined in CLAUDE.md
- For each field in the schema, create a field entry following the type mapping table in CLAUDE.md
- Each collection always starts with an `id` field (uuid, hidden, readonly, sort: 1)
- Field `sort` values are sequential starting from 1; `id` is always 1
- Determine field type by inspecting the actual values in schema.json:
  - Boolean → `boolean`
  - Integer number → `integer`
  - Long string (descriptions, notes) → `text`
  - Short string (names, categories, URLs) → `string`
  - Object or array → `json`
- Refer to `examples/snapshot_eg.json` for the exact field/collection meta structure and boilerplate

## Step 5 — Verify

After writing both files:
1. Confirm `output/schema.json` has all 4 top-level keys and no collection is empty
2. Confirm `output/snapshot.json` has exactly 4 collections and that every field in schema.json has a corresponding field entry in the snapshot
3. Confirm field counts match between schema and snapshot (excluding `id`)
4. Report a summary: property name, apartment count, experience count, service count, total snapshot fields

## Step 6 — Upload to Directus

Run:
```bash
python upload.py
```

Report the output to the user. If it succeeds, confirm that both the schema (collections/fields) and data (items) have been uploaded.
