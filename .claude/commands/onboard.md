Generate the Directus schema and snapshot for a new property onboarding.

## Step 1 — Identify the property name

Ask the user for the property identifier if not already given (e.g. `villa_rossi`). This will be used as `{name}` throughout. It must be lowercase snake_case.

## Step 2 — Check sources

- Verify `website/exported.md` exists. If not, stop and ask the user to run `python website/main.py` first.
- Check whether `information/` contains any files (do not read them yet — just list).

## Step 3 — Extract data via sub-agent

Spawn a **general-purpose sub-agent** with the following task:

> You are generating a Directus onboarding schema for the property **{name}**.
>
> Read every source file:
> - `website/exported.md` — full scraped website
> - Every file inside `information/` (if any exist)
>
> Follow CLAUDE.md strictly for all field naming, type mapping, and output formats.
>
> Produce two output files:
>
> **`output/schema.json`** — all structured property data. Rules:
> - 4 top-level keys: the unit collection key (`apartments` or `rooms`), `experiences`, `services`, `{name}`
> - Extract every distinct unit, experience, and service mentioned in the sources
> - Merge all sources (internal docs take priority over website for accuracy)
> - Use `null` for missing values; all items in a collection must share identical field sets
> - `{name}` is a singleton array with one object capturing all property-level info
>
> **`output/snapshot_input.json`** — minimal field descriptor for `to_snapshot.py`. Rules:
> - `id` and `additional_info` are added automatically — do not include them
> - Include every field present in schema.json
> - Use `select-dropdown` + `choices` for any categorical field with a fixed enum
> - Do NOT read `examples/schema_eg.json` or `examples/snapshot_eg.json` — the type tables in CLAUDE.md are sufficient
>
> Return a brief summary: unit_collection choice, apartment/room count, experience count, service count, field counts per collection.

Wait for the sub-agent to complete before continuing.

## Step 4 — Compile snapshot

Run:
```bash
python to_snapshot.py
```

## Step 5 — Upload to Directus

Run:
```bash
python upload.py
```

## Step 6 — Report to user

Report the sub-agent's summary plus the upload output. Confirm both schema (collections/fields) and data (items) were uploaded.
