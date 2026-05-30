#!/usr/bin/env python3
"""
Set up fleet tracking in InvenTree.

Creates:
- "Machines" category with sub-categories per family
- Machine location hierarchy: Shop, Field, Repair, Out of Service
- Part templates for each machine family (TracStar 618/900/1200)
- Individual stock items for each machine (with serial numbers)

Run once after InvenTree is initialized.
Safe to re-run — skips existing items.
"""
import json
import urllib.request
import urllib.parse
import base64
import os
import sys
import time


BASE = os.environ.get("INVENTREE_SITE_URL", "http://localhost:8080")
USER = os.environ.get("INVENTREE_ADMIN_USER", "shopmanager")
PASS = os.environ.get("INVENTREE_ADMIN_PASSWORD", "")

if not PASS:
    # Try .env file
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("INVENTREE_ADMIN_PASSWORD="):
                PASS = line.split("=", 1)[1].strip()

if not PASS:
    print("ERROR: Set INVENTREE_ADMIN_PASSWORD in .env or environment")
    sys.exit(1)

FAMILIES = [
    {"family": "618", "model": "TracStar 618", "count": 20, "engine": "Kubota D1105", "prefix": "UGSI-618"},
    {"family": "900", "model": "TracStar 900", "count": 12, "engine": "Kubota V2403", "prefix": "UGSI-900"},
    {"family": "1200", "model": "TracStar 1200", "count": 4, "engine": "Kubota V3307", "prefix": "UGSI-1200"},
]

# Machine status locations
STATUS_LOCATIONS = [
    {"name": "Shop", "description": "Machines at the shop"},
    {"name": "Field", "description": "Machines deployed to job sites"},
    {"name": "Repair", "description": "Machines needing repair"},
    {"name": "Out of Service", "description": "Machines out of service"},
]


def get_token():
    cred = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
    req = urllib.request.Request(f"{BASE}/api/user/token/")
    req.add_header("Authorization", f"Basic {cred}")
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())["token"]


def api(endpoint, method="GET", body=None, params=None, token=""):
    url = f"{BASE}/api/{endpoint.strip('/')}/"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Token {token}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        text = e.read().decode() if e.fp else ""
        if e.code == 400 and "already exists" in text.lower():
            return None  # Skip duplicates
        raise RuntimeError(f"API {e.code}: {text[:200]}")


def find_or_create(endpoint, search_params, create_body, token):
    """Find existing item or create new one."""
    results = api(endpoint, params=search_params, token=token)
    if isinstance(results, list):
        items = results
    else:
        items = results.get("results", [])
    if items:
        return items[0]
    try:
        result = api(endpoint, method="POST", body=create_body, token=token)
        return result
    except RuntimeError as e:
        if "already exists" in str(e).lower():
            # Re-fetch
            results = api(endpoint, params=search_params, token=token)
            items = results.get("results", [])
            return items[0] if items else None
        raise


def main():
    print("Setting up fleet tracking in InvenTree...")
    print(f"  Server: {BASE}")
    print(f"  User: {USER}")

    token = get_token()
    print(f"  Auth: OK\n")

    # 1. Create "Machines" category
    print("1. Creating machine categories...")
    machines_cat = find_or_create(
        "part/category",
        {"name": "Machines"},
        {"name": "Machines", "description": "McElroy butt-fusion machines - fleet tracking"},
        token
    )
    machines_cat_pk = machines_cat["pk"]
    print(f"   Machines category: pk={machines_cat_pk}")

    family_cats = {}
    for fam in FAMILIES:
        cat = find_or_create(
            "part/category",
            {"name": fam["model"], "parent": machines_cat_pk},
            {"name": fam["model"], "parent": machines_cat_pk,
             "description": f"{fam['model']} ({fam['engine']}) - {fam['count']} units"},
            token
        )
        family_cats[fam["family"]] = cat["pk"]
        print(f"   {fam['model']}: pk={cat['pk']}")

    # 2. Create machine status locations (under a "Fleet" parent)
    print("\n2. Creating fleet locations...")
    fleet_loc = find_or_create(
        "stock/location",
        {"name": "Fleet"},
        {"name": "Fleet", "description": "Machine fleet locations"},
        token
    )
    fleet_loc_pk = fleet_loc["pk"]

    status_locs = {}
    for loc in STATUS_LOCATIONS:
        result = find_or_create(
            "stock/location",
            {"name": loc["name"], "parent": fleet_loc_pk},
            {"name": loc["name"], "parent": fleet_loc_pk, "description": loc["description"]},
            token
        )
        status_locs[loc["name"]] = result["pk"]
        print(f"   {loc['name']}: pk={result['pk']}")

    # 3. Create machine part templates (one per family)
    print("\n3. Creating machine part templates...")
    family_parts = {}
    for fam in FAMILIES:
        part = find_or_create(
            "part",
            {"IPN": fam["prefix"]},
            {
                "name": fam["model"],
                "IPN": fam["prefix"],
                "description": f"{fam['model']} butt-fusion machine ({fam['engine']} engine)",
                "category": family_cats[fam["family"]],
                "trackable": True,  # Enables serial number tracking
                "is_template": False,
                "assembly": False,
                "purchaseable": True,
                "salable": False,
                "active": True,
                "notes": f"Engine: {fam['engine']}. Fleet of {fam['count']} units.",
            },
            token
        )
        family_parts[fam["family"]] = part["pk"]
        print(f"   {fam['model']}: pk={part['pk']} (trackable=True)")

    # 4. Create individual machine stock items with serial numbers
    print("\n4. Creating individual machines...")
    created = 0
    skipped = 0
    for fam in FAMILIES:
        part_pk = family_parts[fam["family"]]
        for i in range(1, fam["count"] + 1):
            serial = f"{fam['prefix']}-{str(i).zfill(3)}"

            # Check if already exists
            existing = api("stock", params={"part": part_pk, "serial": serial}, token=token)
            items = existing if isinstance(existing, list) else existing.get("results", [])
            if items:
                skipped += 1
                continue

            try:
                result = api("stock", method="POST", body={
                    "part": part_pk,
                    "quantity": 1,
                    "location": status_locs["Shop"],  # Default: all machines start at shop
                    "notes": json.dumps({
                        "engine_type": fam["engine"],
                        "engine_serial": "",
                        "hours": "",
                        "job": "",
                        "location_detail": "",
                    }),
                }, token=token)
                # InvenTree ignores serial on POST — must PATCH after creation
                if result:
                    items = result if isinstance(result, list) else [result]
                    for item in items:
                        if item and item.get("pk"):
                            api(f"stock/{item['pk']}", method="PATCH",
                                body={"serial": serial}, token=token)
                created += 1
                if created % 10 == 0:
                    print(f"   Created {created} machines...")
            except RuntimeError as e:
                print(f"   WARNING: {serial}: {e}")
                skipped += 1

    print(f"   Done: {created} created, {skipped} already existed")

    # Summary
    print(f"\n{'='*50}")
    print(f"Fleet setup complete!")
    print(f"  Machine categories: {len(family_cats)}")
    print(f"  Status locations: {len(status_locs)}")
    print(f"  Machine templates: {len(family_parts)}")
    print(f"  Individual machines: {created + skipped}")
    print(f"\nMachine status locations (under Fleet):")
    for name, pk in status_locs.items():
        print(f"  {name}: pk={pk}")
    print(f"\nMachines are tracked as serial-numbered stock items.")
    print(f"Move a machine between Shop/Field/Repair to change its status.")


if __name__ == "__main__":
    main()
