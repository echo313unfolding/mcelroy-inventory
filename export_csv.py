#!/usr/bin/env python3
"""
Export parts data as CSV files for InvenTree bulk import.
These can be imported directly through the InvenTree web UI
without needing the API script.

Output:
  csv/categories.csv  — Part categories
  csv/parts.csv       — Parts with category paths
  csv/locations.csv   — Stock locations
  csv/machines.csv    — Fleet machine list
"""

import csv
from pathlib import Path
from parts_data import CATEGORIES, PARTS, STOCK_LOCATIONS, MACHINE_MODELS, FLEET_TEMPLATE

OUT = Path(__file__).parent / "csv"
OUT.mkdir(exist_ok=True)


def export_categories():
    with open(OUT / "categories.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Category Name", "Parent Category", "Description"])
        for cat in CATEGORIES:
            w.writerow([cat["name"], cat.get("parent", ""), cat.get("description", "")])
    print(f"  categories.csv: {len(CATEGORIES)} categories")


def export_parts():
    with open(OUT / "parts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "Part Name", "Category", "Description", "IPN (McElroy PN)",
            "Compatible Machines", "Trackable (Serialized)", "Purchaseable",
            "Minimum Stock", "Reorder Quantity", "Is Consumable",
        ])
        for part in PARTS:
            w.writerow([
                part["name"],
                part["category"],
                part.get("description", ""),
                part.get("mcelroy_pn", ""),
                ", ".join(part.get("machines", [])),
                "Yes" if part.get("is_serialized") else "No",
                "Yes",
                part.get("reorder_point", 0),
                part.get("reorder_qty", 0),
                "Yes" if part.get("is_consumable") else "No",
            ])
    print(f"  parts.csv: {len(PARTS)} parts")


def export_locations():
    with open(OUT / "locations.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Location Name", "Parent Location", "Description"])
        for loc in STOCK_LOCATIONS:
            w.writerow([loc["name"], loc.get("parent", ""), loc.get("description", "")])
    print(f"  locations.csv: {len(STOCK_LOCATIONS)} locations")


def export_machines():
    with open(OUT / "machines.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "Machine ID", "Model", "Family", "Variant",
            "Pipe Range", "Power", "Serial Number",
        ])
        for family, config in FLEET_TEMPLATE.items():
            model_info = next(
                (m for m in MACHINE_MODELS if m["family"] == family and "TracStar" in m["model"]),
                None,
            )
            if not model_info:
                continue

            prefix = config["prefix"]

            for i in range(1, config["count_standard"] + 1):
                w.writerow([
                    f"{prefix}-{i:03d}",
                    model_info["model"],
                    family,
                    "Standard",
                    model_info["pipe_range"],
                    model_info["power"],
                    "[ENTER SERIAL]",
                ])

            if model_info.get("model_i"):
                for i in range(1, config["count_i_series"] + 1):
                    w.writerow([
                        f"{prefix}i-{i:03d}",
                        model_info["model_i"],
                        family,
                        "i-series",
                        model_info["pipe_range"],
                        model_info["power"],
                        "[ENTER SERIAL]",
                    ])

    total = sum(c["count_standard"] + c["count_i_series"] for c in FLEET_TEMPLATE.values())
    print(f"  machines.csv: {total} machines")


def main():
    print("Exporting CSV files for InvenTree import...")
    export_categories()
    export_parts()
    export_locations()
    export_machines()
    print(f"\nFiles in: {OUT}/")
    print("\nTo import: InvenTree web UI → Admin → Import Data → upload CSVs")


if __name__ == "__main__":
    main()
