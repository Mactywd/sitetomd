"""
Upload snapshot.json and schema.json to a Directus instance.

Usage:
    python upload.py                  # upload snapshot + schema data
    python upload.py --dry-run        # preview snapshot diff, skip data upload
    python upload.py --skip-schema    # upload snapshot only, skip data upload
    python upload.py --skip-snapshot  # upload data only, skip snapshot

The snapshot upload fetches the current schema, merges only additions, then applies.
The schema upload skips any collection that already has items (safe to re-run).
"""

import argparse
import json
import sys
import requests


CHILD_KEYS = {"apartments", "experiences", "services"}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_snapshot(path):
    data = load_json(path)
    return data.get("data", data)  # unwrap {"data": ...} wrapper if present


def parse_schema(schema):
    """Return (name, {key: [items]}) from schema.json array."""
    schema_dict = {}
    name = None
    for item in schema:
        key = next(iter(item))
        schema_dict[key] = item[key]
        if key not in CHILD_KEYS:
            name = key
    if not name:
        raise ValueError("Could not determine property name from schema.json")
    return name, schema_dict


# ── Snapshot upload ────────────────────────────────────────────────────────────

def fetch_current(base_url, token):
    resp = requests.get(
        f"{base_url}/schema/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json().get("data", resp.json())


def merge(current, incoming):
    """Merge incoming snapshot into current — additions only."""
    merged = {**current}

    existing_collections = {c["collection"] for c in current.get("collections", [])}
    merged["collections"] = current.get("collections", []) + [
        c for c in incoming.get("collections", [])
        if c["collection"] not in existing_collections
    ]

    existing_fields = {(f["collection"], f["field"]) for f in current.get("fields", [])}
    merged["fields"] = current.get("fields", []) + [
        f for f in incoming.get("fields", [])
        if (f["collection"], f["field"]) not in existing_fields
    ]

    existing_relations = {
        (r.get("collection"), r.get("field")) for r in current.get("relations", [])
    }
    merged["relations"] = current.get("relations", []) + [
        r for r in incoming.get("relations", [])
        if (r.get("collection"), r.get("field")) not in existing_relations
    ]

    return merged


def get_diff(base_url, token, snapshot):
    resp = requests.post(
        f"{base_url}/schema/diff",
        headers={"Authorization": f"Bearer {token}"},
        json=snapshot,
    )
    if resp.status_code == 204:
        return None
    resp.raise_for_status()
    return resp.json()


def apply_diff(base_url, token, diff):
    payload = diff.get("data", diff)
    resp = requests.post(
        f"{base_url}/schema/apply",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    resp.raise_for_status()


def summarise_diff(diff):
    data = diff.get("data", diff)
    changes = data.get("diff", data)
    lines = []
    for section, ops in changes.items():
        if not ops:
            continue
        if isinstance(ops, dict):
            for op, items in ops.items():
                if items:
                    lines.append(f"  {section} → {op}: {len(items)} item(s)")
        else:
            lines.append(f"  {section}: {len(ops)} change(s)")
    return "\n".join(lines) if lines else "  (empty diff)"


def upload_snapshot(base_url, token, snapshot_path, dry_run):
    print(f"\n── Snapshot: {snapshot_path}")
    incoming = load_snapshot(snapshot_path)

    print(f"Fetching current schema from {base_url} ...")
    current = fetch_current(base_url, token)

    merged = merge(current, incoming)
    new_c = len(merged["collections"]) - len(current.get("collections", []))
    new_f = len(merged["fields"]) - len(current.get("fields", []))
    print(f"Merging: +{new_c} collections, +{new_f} fields")

    diff = get_diff(base_url, token, merged)
    if diff is None:
        print("No schema changes — already up to date.")
        return

    print("Changes detected:")
    print(summarise_diff(diff))

    if dry_run:
        print("--dry-run set, skipping apply.")
        return

    print("Applying ...")
    apply_diff(base_url, token, diff)
    print("Snapshot applied.")


# ── Schema data upload ─────────────────────────────────────────────────────────

def collection_is_empty(base_url, token, collection):
    """Return True if the collection has no items yet."""
    resp = requests.get(
        f"{base_url}/items/{collection}",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 1, "fields": "id"},
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    # Singleton returns a dict (or null), list collections return an array
    if isinstance(data, list):
        return len(data) == 0
    return data is None


def upload_schema(base_url, token, schema_path):
    print(f"\n── Schema data: {schema_path}")
    schema = load_json(schema_path)
    name, schema_dict = parse_schema(schema)
    headers = {"Authorization": f"Bearer {token}"}

    # Child collections
    for key in ["apartments", "experiences", "services"]:
        collection = f"{name}_{key}"
        items = schema_dict.get(key, [])
        if not items:
            print(f"  {collection}: no items, skipping")
            continue
        if not collection_is_empty(base_url, token, collection):
            print(f"  {collection}: already has data, skipping")
            continue
        resp = requests.post(
            f"{base_url}/items/{collection}",
            headers=headers,
            json=items,
        )
        resp.raise_for_status()
        print(f"  {collection}: {len(items)} items uploaded")

    # Singleton — check by fetching and inspecting the id field
    singleton_items = schema_dict.get(name, [])
    if not singleton_items:
        print(f"  {name}: no data, skipping")
        return
    singleton_data = singleton_items[0]
    existing = requests.get(f"{base_url}/items/{name}", headers=headers)
    existing.raise_for_status()
    existing_data = existing.json().get("data") or {}
    if existing_data.get("id"):
        print(f"  {name}: already has data, skipping")
        return
    resp = requests.patch(
        f"{base_url}/items/{name}",
        headers=headers,
        json=singleton_data,
    )
    resp.raise_for_status()
    print(f"  {name}: singleton uploaded")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload snapshot and schema data to Directus")
    parser.add_argument("--url", default="http://157.180.24.240:8055")
    parser.add_argument("--token", default="25abdT3eZ_-nnCyfOCdpVTJL8y5U_FIT")
    parser.add_argument("--snapshot", default="output/snapshot.json")
    parser.add_argument("--schema", default="output/schema.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview snapshot diff, skip data upload")
    parser.add_argument("--skip-snapshot", action="store_true")
    parser.add_argument("--skip-schema", action="store_true")
    args = parser.parse_args()

    if not args.skip_snapshot:
        upload_snapshot(args.url, args.token, args.snapshot, args.dry_run)

    if not args.skip_schema and not args.dry_run:
        upload_schema(args.url, args.token, args.schema)

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
