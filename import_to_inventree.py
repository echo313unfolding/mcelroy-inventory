#!/usr/bin/env python3
"""
Import McElroy parts data into InvenTree via REST API.

Usage:
    # After docker compose up:
    python3 import_to_inventree.py

    # With custom URL/credentials:
    python3 import_to_inventree.py --url http://localhost:8080 --user shopmanager --password ugsi2026!

Requires: pip install requests
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

from parts_data import CATEGORIES, PARTS, STOCK_LOCATIONS, MACHINE_MODELS, FLEET_TEMPLATE


class InvenTreeImporter:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api"
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.session.auth = (username, password)

        # Verify credentials
        print(f"Authenticating to {self.base_url}...")
        resp = self.session.get(f"{self.api_url}/user/me/")
        if resp.status_code != 200:
            print(f"Auth failed: {resp.status_code} {resp.text}")
            sys.exit(1)

        print(f"  Authenticated as {username}")

    def api_get(self, endpoint, params=None):
        resp = self.session.get(f"{self.api_url}/{endpoint}/", params=params)
        resp.raise_for_status()
        return resp.json()

    def api_post(self, endpoint, data):
        resp = self.session.post(f"{self.api_url}/{endpoint}/", json=data)
        if resp.status_code not in (200, 201):
            print(f"  POST {endpoint} failed: {resp.status_code}")
            print(f"  Data: {json.dumps(data)[:200]}")
            print(f"  Response: {resp.text[:300]}")
            return None
        return resp.json()

    # ---- Categories ----
    def import_categories(self):
        print("\n=== Importing Part Categories ===")
        cat_map = {}  # name -> id

        # Get existing categories
        existing = self.api_get("part/category")
        if isinstance(existing, list):
            for cat in existing:
                cat_map[cat["name"]] = cat["pk"]

        for cat in CATEGORIES:
            if cat["name"] in cat_map:
                print(f"  [exists] {cat['name']}")
                continue

            data = {
                "name": cat["name"],
                "description": cat.get("description", ""),
            }
            if cat.get("parent") and cat["parent"] in cat_map:
                data["parent"] = cat_map[cat["parent"]]

            result = self.api_post("part/category", data)
            if result:
                cat_map[result["name"]] = result["pk"]
                print(f"  [created] {cat['name']} (id={result['pk']})")
            else:
                print(f"  [FAILED] {cat['name']}")

        self.cat_map = cat_map
        return cat_map

    # ---- Stock Locations ----
    def import_stock_locations(self):
        print("\n=== Importing Stock Locations ===")
        loc_map = {}

        existing = self.api_get("stock/location")
        if isinstance(existing, list):
            for loc in existing:
                loc_map[loc["name"]] = loc["pk"]

        for loc in STOCK_LOCATIONS:
            if loc["name"] in loc_map:
                print(f"  [exists] {loc['name']}")
                continue

            data = {
                "name": loc["name"],
                "description": loc.get("description", ""),
            }
            if loc.get("parent") and loc["parent"] in loc_map:
                data["parent"] = loc_map[loc["parent"]]

            result = self.api_post("stock/location", data)
            if result:
                loc_map[result["name"]] = result["pk"]
                print(f"  [created] {loc['name']} (id={result['pk']})")

        self.loc_map = loc_map
        return loc_map

    # ---- Parts ----
    def import_parts(self):
        print("\n=== Importing Parts ===")
        part_map = {}

        existing = self.api_get("part", params={"limit": 500})
        if isinstance(existing, dict) and "results" in existing:
            existing = existing["results"]
        if isinstance(existing, list):
            for part in existing:
                part_map[part["name"]] = part["pk"]

        for part in PARTS:
            if part["name"] in part_map:
                print(f"  [exists] {part['name']}")
                continue

            cat_id = self.cat_map.get(part["category"])
            if not cat_id:
                print(f"  [SKIP] {part['name']} — category '{part['category']}' not found")
                continue

            data = {
                "name": part["name"],
                "description": part.get("description", ""),
                "category": cat_id,
                "active": True,
                "component": True,
                "purchaseable": True,
                "trackable": part.get("is_serialized", False),
                "is_template": False,
                "virtual": False,
            }

            # Add IPN (Internal Part Number) from McElroy PN
            if part.get("mcelroy_pn"):
                data["IPN"] = part["mcelroy_pn"]

            # Add notes with machine compatibility
            machines = part.get("machines", [])
            if machines:
                data["notes"] = f"Compatible machines: {', '.join(machines)}"

            # Set minimum stock level
            if part.get("reorder_point"):
                data["minimum_stock"] = part["reorder_point"]

            result = self.api_post("part", data)
            if result:
                part_map[result["name"]] = result["pk"]
                print(f"  [created] {part['name']} (id={result['pk']}, IPN={data.get('IPN', '-')})")
            else:
                print(f"  [FAILED] {part['name']}")

        self.part_map = part_map
        return part_map

    # ---- Machine instances as stock locations ----
    def import_fleet(self):
        print("\n=== Importing Fleet (Machines as Stock Locations) ===")

        # Create "Fleet" parent location
        fleet_loc = self.api_post("stock/location", {
            "name": "Fleet - Active Machines",
            "description": "All machines currently in service",
        })
        if not fleet_loc:
            # Try to find existing
            existing = self.api_get("stock/location", params={"name": "Fleet - Active Machines"})
            if isinstance(existing, list) and existing:
                fleet_loc = existing[0]
            elif isinstance(existing, dict) and "results" in existing and existing["results"]:
                fleet_loc = existing["results"][0]
            else:
                print("  Could not create Fleet location")
                return

        fleet_id = fleet_loc["pk"]
        print(f"  Fleet parent location: id={fleet_id}")

        machine_count = 0
        for family, config in FLEET_TEMPLATE.items():
            # Find matching model
            model_info = next((m for m in MACHINE_MODELS if m["family"] == family and "TracStar" in m["model"]), None)
            if not model_info:
                continue

            # Create family sub-location
            family_loc = self.api_post("stock/location", {
                "name": f"{family} Family",
                "parent": fleet_id,
                "description": f"All {family}-class machines. {model_info['pipe_range']}",
            })
            if not family_loc:
                continue
            family_loc_id = family_loc["pk"]

            prefix = config["prefix"]

            # Standard machines
            for i in range(1, config["count_standard"] + 1):
                name = f"{prefix}-{i:03d}"
                loc = self.api_post("stock/location", {
                    "name": name,
                    "parent": family_loc_id,
                    "description": f"{model_info['model']} (Standard). {model_info['pipe_range']}. SN: [enter serial]",
                })
                if loc:
                    machine_count += 1

            # i-series machines
            if model_info.get("model_i"):
                for i in range(1, config["count_i_series"] + 1):
                    name = f"{prefix}i-{i:03d}"
                    loc = self.api_post("stock/location", {
                        "name": name,
                        "parent": family_loc_id,
                        "description": f"{model_info['model_i']} (i-series). {model_info['pipe_range']}. SN: [enter serial]",
                    })
                    if loc:
                        machine_count += 1

        print(f"\n  Created {machine_count} machine locations")

    # ---- Custom parameters for McElroy-specific fields ----
    def import_parameters(self):
        print("\n=== Creating Custom Part Parameters ===")

        params = [
            {"name": "McElroy Part Number", "units": "", "description": "Official McElroy part number"},
            {"name": "Pipe Size", "units": "inches", "description": "Compatible pipe size (IPS or DIPS)"},
            {"name": "Machine Family", "units": "", "description": "618, 900, or 1200"},
            {"name": "Force Rating", "units": "", "description": "High (Green), Medium (Orange), Low (Yellow)"},
            {"name": "Voltage", "units": "V", "description": "Electrical voltage requirement"},
            {"name": "Filter Micron", "units": "micron", "description": "Filter element micron rating"},
            {"name": "Service Interval", "units": "hours", "description": "Recommended service/replacement interval"},
        ]

        for param in params:
            result = self.api_post("part/parameter/template", param)
            if result:
                print(f"  [created] {param['name']}")
            else:
                print(f"  [skip/exists] {param['name']}")

    def run_full_import(self):
        print("=" * 60)
        print("McElroy Parts Import to InvenTree")
        print("Underground Solutions - Fusible PVC Fleet")
        print("=" * 60)

        self.import_categories()
        self.import_stock_locations()
        self.import_parameters()
        self.import_parts()
        self.import_fleet()

        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print(f"  Categories: {len(self.cat_map)}")
        print(f"  Locations:  {len(self.loc_map)}")
        print(f"  Parts:      {len(self.part_map)}")
        print("=" * 60)

        print("\nNext steps:")
        print("  1. Log in at http://localhost:8080")
        print("  2. Add machine serial numbers to fleet locations")
        print("  3. Set initial stock quantities")
        print("  4. Add actual McElroy part numbers from Parts Finder")
        print("  5. Set up barcode scanning on phones")


def main():
    parser = argparse.ArgumentParser(description="Import McElroy parts into InvenTree")
    parser.add_argument("--url", default="http://localhost:8080", help="InvenTree base URL")
    parser.add_argument("--user", default="shopmanager", help="Admin username")
    parser.add_argument("--password", default="ugsi2026!", help="Admin password")
    args = parser.parse_args()

    importer = InvenTreeImporter(args.url, args.user, args.password)
    importer.run_full_import()


if __name__ == "__main__":
    main()
