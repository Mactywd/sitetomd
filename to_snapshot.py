#!/usr/bin/env python3
"""
Compile a full Directus snapshot.json from a minimal field descriptor.

Usage:
    python to_snapshot.py                          # reads output/snapshot_input.json
    python to_snapshot.py path/to/input.json       # reads specified file

Output: output/snapshot.json

Minimal input format:
{
  "name": "chiusella",           // snake_case property identifier
  "unit_collection": "apartments",  // "apartments" or "rooms"
  "property": [                  // fields for the singleton collection (no additional_info)
    {"field": "property_name", "type": "string"},
    {"field": "property_description", "type": "text"}
  ],
  "units": [                     // fields for {name}_apartments or {name}_rooms
    {"field": "apartment_name", "type": "string"},
    {"field": "apartment_max_occupancy", "type": "integer"},
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

Supported types:
  string   → short text (≤255), input
  text     → long text, WYSIWYG (input-rich-text-html)
  integer  → integer, input
  float    → decimal, input
  boolean  → toggle, boolean interface
  datetime → timestamp, datetime interface
  json     → free-form tags list, tags interface
  image    → single image file reference
  file     → single file reference

Optional per-field overrides:
  "interface": "<directus-interface>"  override the default interface
  "choices": ["A", "B", ...]           for select-dropdown / select-multiple-dropdown;
                                        values become both text and value labels
"""

import json
import os
import sys

# Maps semantic type → (directus_type, data_type, default_interface, special, max_length, numeric_precision, numeric_scale)
TYPE_MAP = {
    "string":   ("string",   "character varying",        "input",                None,             255,  None, None),
    "text":     ("text",     "text",                     "input-rich-text-html", None,             None, None, None),
    "integer":  ("integer",  "integer",                  "input",                None,             None, 32,   0),
    "float":    ("float",    "real",                     "input",                None,             None, None, None),
    "boolean":  ("boolean",  "boolean",                  "boolean",              ["cast-boolean"], None, None, None),
    "datetime": ("dateTime", "timestamp with time zone", "datetime",             None,             None, None, None),
    "json":     ("json",     "jsonb",                    "tags",                 ["cast-json"],    None, None, None),
    "image":    ("uuid",     "uuid",                     "file-image",           ["file"],         None, None, None),
    "file":     ("uuid",     "uuid",                     "file",                 ["file"],         None, None, None),
}

# Interface overrides that change the underlying Directus type/special
INTERFACE_TYPE_OVERRIDES = {
    "select-multiple-dropdown": {
        "directus_type": "json",
        "data_type": "jsonb",
        "special": ["cast-json"],
        "max_length": None,
        "numeric_precision": None,
        "numeric_scale": None,
    },
}


def make_id_field(collection):
    return {
        "collection": collection,
        "field": "id",
        "type": "uuid",
        "meta": {
            "collection": collection,
            "conditions": None,
            "display": None,
            "display_options": None,
            "field": "id",
            "group": None,
            "hidden": True,
            "interface": "input",
            "note": None,
            "options": None,
            "readonly": True,
            "required": False,
            "searchable": True,
            "sort": 1,
            "special": ["uuid"],
            "translations": None,
            "validation": None,
            "validation_message": None,
            "width": "full",
        },
        "schema": {
            "name": "id",
            "table": collection,
            "data_type": "uuid",
            "default_value": None,
            "max_length": None,
            "numeric_precision": None,
            "numeric_scale": None,
            "is_nullable": False,
            "is_unique": True,
            "is_indexed": False,
            "is_primary_key": True,
            "is_generated": False,
            "generation_expression": None,
            "has_auto_increment": False,
            "foreign_key_table": None,
            "foreign_key_column": None,
        },
    }


def make_field(collection, field_def, sort):
    semantic_type = field_def["type"]
    if semantic_type not in TYPE_MAP:
        raise ValueError(f"Unknown type '{semantic_type}' for field '{field_def['field']}'. "
                         f"Valid types: {', '.join(TYPE_MAP)}")

    directus_type, data_type, default_interface, special, max_length, num_prec, num_scale = TYPE_MAP[semantic_type]

    interface = field_def.get("interface", default_interface)

    # Apply interface-driven type overrides (e.g. select-multiple-dropdown forces json)
    if interface in INTERFACE_TYPE_OVERRIDES:
        overrides = INTERFACE_TYPE_OVERRIDES[interface]
        directus_type = overrides["directus_type"]
        data_type = overrides["data_type"]
        special = overrides["special"]
        max_length = overrides["max_length"]
        num_prec = overrides["numeric_precision"]
        num_scale = overrides["numeric_scale"]

    # Build options for dropdown interfaces
    options = None
    if "choices" in field_def:
        options = {
            "choices": [
                {"text": c, "value": c} if isinstance(c, str) else c
                for c in field_def["choices"]
            ]
        }

    field_name = field_def["field"]

    return {
        "collection": collection,
        "field": field_name,
        "type": directus_type,
        "meta": {
            "collection": collection,
            "conditions": None,
            "display": None,
            "display_options": None,
            "field": field_name,
            "group": None,
            "hidden": False,
            "interface": interface,
            "note": None,
            "options": options,
            "readonly": False,
            "required": False,
            "searchable": True,
            "sort": sort,
            "special": special,
            "translations": None,
            "validation": None,
            "validation_message": None,
            "width": "full",
        },
        "schema": {
            "name": field_name,
            "table": collection,
            "data_type": data_type,
            "default_value": None,
            "max_length": max_length,
            "numeric_precision": num_prec,
            "numeric_scale": num_scale,
            "is_nullable": True,
            "is_unique": False,
            "is_indexed": False,
            "is_primary_key": False,
            "is_generated": False,
            "generation_expression": None,
            "has_auto_increment": False,
            "foreign_key_table": None,
            "foreign_key_column": None,
        },
    }


def make_additional_info(collection, sort):
    return make_field(
        collection,
        {"field": "additional_info", "type": "text", "interface": "textarea"},
        sort,
    )


def build_collection_fields(collection_name, field_defs, include_additional_info):
    fields = [make_id_field(collection_name)]
    for i, fd in enumerate(field_defs, start=2):
        fields.append(make_field(collection_name, fd, i))
    if include_additional_info:
        fields.append(make_additional_info(collection_name, len(field_defs) + 2))
    return fields


def make_collection_meta(collection_name, singleton, group, sort):
    return {
        "collection": collection_name,
        "meta": {
            "accountability": "all",
            "archive_app_filter": True,
            "archive_field": None,
            "archive_value": None,
            "collapse": "open",
            "collection": collection_name,
            "color": None,
            "display_template": None,
            "group": group,
            "hidden": False,
            "icon": None,
            "item_duplication_fields": None,
            "note": None,
            "preview_url": None,
            "singleton": singleton,
            "sort": sort,
            "sort_field": None,
            "translations": None,
            "unarchive_value": None,
            "versioning": False,
        },
        "schema": {"name": collection_name},
    }


def build_snapshot(inp):
    name = inp["name"]
    unit_collection = inp.get("unit_collection", "apartments")

    col_property = name
    col_units = f"{name}_{unit_collection}"
    col_experiences = f"{name}_experiences"
    col_services = f"{name}_services"

    collections = [
        make_collection_meta(col_property,    singleton=True,  group=None, sort=1),
        make_collection_meta(col_units,        singleton=False, group=name, sort=1),
        make_collection_meta(col_experiences,  singleton=False, group=name, sort=2),
        make_collection_meta(col_services,     singleton=False, group=name, sort=3),
    ]

    fields = []
    fields += build_collection_fields(col_property,   inp.get("property",    []), include_additional_info=False)
    fields += build_collection_fields(col_units,       inp.get("units",       []), include_additional_info=True)
    fields += build_collection_fields(col_experiences, inp.get("experiences", []), include_additional_info=True)
    fields += build_collection_fields(col_services,    inp.get("services",    []), include_additional_info=True)

    return {
        "data": {
            "version": 1,
            "directus": "11.15.4",
            "vendor": "postgres",
            "collections": collections,
            "fields": fields,
            "relations": [],
        }
    }


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "output/snapshot_input.json"

    if not os.path.exists(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path) as f:
        inp = json.load(f)

    snapshot = build_snapshot(inp)

    os.makedirs("output", exist_ok=True)
    out_path = "output/snapshot.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    total_fields = len(snapshot["data"]["fields"])
    total_collections = len(snapshot["data"]["collections"])
    print(f"Written {out_path}  ({total_collections} collections, {total_fields} fields)")


if __name__ == "__main__":
    main()
