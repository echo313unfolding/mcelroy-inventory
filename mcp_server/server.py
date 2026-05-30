"""
UGSI McElroy Shop — MCP Server

Exposes inventory, fleet, and reporting tools for LLM agents.
Runs as a stdio MCP server (for Claude Code) or HTTP (for other clients).

Usage:
  python -m mcp_server.server          # stdio mode (Claude Code)
  python -m mcp_server.server --http   # HTTP mode on configured port

Tools provided:
  - lookup_machine: Look up a machine by ID, show compatible parts + stock
  - lookup_part: Search for a part by name, SKU, or description
  - check_stock: Check stock levels for a part or across all parts
  - adjust_stock: Add or remove stock (requires write mode)
  - fleet_status: List machines filtered by status, family, or job
  - low_stock_report: Parts below reorder point
  - inventory_snapshot: Full inventory summary
  - system_health: Check InvenTree connection and config status
  - get_config: Read current configuration
  - set_config: Update configuration (dev mode, integrations, etc.)
  - import_csv: Import parts/stock data from CSV (legacy system migration)
"""
import sys
import json
import csv
import io
import logging
from pathlib import Path

from .config import load_config, save_config
from .inventree_client import InvenTreeClient

# Machine families (matches the shop app)
FAMILIES = [
    {"family": "618", "model": "TracStar 618", "count": 20, "engine": "Kubota D1105", "prefix": "UGSI-618"},
    {"family": "900", "model": "TracStar 900", "count": 12, "engine": "Kubota V2403", "prefix": "UGSI-900"},
    {"family": "1200", "model": "TracStar 1200", "count": 4, "engine": "Kubota V3307", "prefix": "UGSI-1200"},
]


class UGSIServer:
    def __init__(self):
        self.config = load_config()
        self.client = InvenTreeClient(self.config)
        self.logger = logging.getLogger("ugsi_mcp")
        level = getattr(logging, self.config.get("log_level", "INFO"))
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    # ── MCP Tool Definitions ──

    def get_tools(self):
        return [
            {
                "name": "lookup_machine",
                "description": "Look up a McElroy fusion machine by ID (e.g. UGSI-618-001). Returns machine info, status, job assignment, and all compatible parts with current stock levels.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "machine_id": {"type": "string", "description": "Machine ID like UGSI-618-001, or partial like 618-001"}
                    },
                    "required": ["machine_id"]
                }
            },
            {
                "name": "lookup_part",
                "description": "Search for a McElroy part by name, SKU/IPN, or keyword. Returns part details, stock levels, compatible machines, and location.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Part name, McElroy part number, or search keyword"},
                        "machine_family": {"type": "string", "enum": ["618", "900", "1200"], "description": "Filter to parts compatible with this machine family"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "check_stock",
                "description": "Check stock level for a specific part or get overall stock status. Returns quantity, location, and reorder status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "part_name": {"type": "string", "description": "Part name or SKU to check (optional — omit for overall status)"},
                        "location": {"type": "string", "description": "Filter to a specific storage location"}
                    }
                }
            },
            {
                "name": "adjust_stock",
                "description": "Add or remove stock for a part at a specific location. Requires write mode to be enabled in settings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "part_query": {"type": "string", "description": "Part name or SKU"},
                        "location": {"type": "string", "description": "Storage location name"},
                        "quantity": {"type": "integer", "description": "Positive to add, negative to remove"},
                        "reason": {"type": "string", "description": "Reason for adjustment (logged)"}
                    },
                    "required": ["part_query", "location", "quantity"]
                }
            },
            {
                "name": "fleet_status",
                "description": "List all McElroy fusion machines with their status, job assignments, and engine hours. Filter by status (Shop/Field/Needs Repair), family (618/900/1200), or job name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["Shop", "Field", "Needs Repair", "Out of Service"]},
                        "family": {"type": "string", "enum": ["618", "900", "1200"]},
                        "job": {"type": "string", "description": "Job name to filter by"}
                    }
                }
            },
            {
                "name": "low_stock_report",
                "description": "List all parts that are at or below their reorder point. Useful for generating purchase orders.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["summary", "detailed", "csv"], "description": "Output format (default: summary)"}
                    }
                }
            },
            {
                "name": "inventory_snapshot",
                "description": "Full inventory summary — total parts, stock value, category breakdown, out-of-stock count.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "system_health",
                "description": "Check system health — InvenTree connection, cache status, config validation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_config",
                "description": "Read current server configuration. Shows dev mode status, enabled integrations, and feature flags.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "description": "Config section to read (e.g. 'integrations', 'dev_mode'). Omit for all."}
                    }
                }
            },
            {
                "name": "set_config",
                "description": "Update server configuration. Changes are persisted to disk. Use for enabling dev mode, integrations, write operations, etc.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Config key (e.g. 'dev_mode', 'enable_write_operations', 'integrations.sharepoint.enabled')"},
                        "value": {"type": ["string", "boolean", "number"], "description": "New value"}
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "import_csv",
                "description": "Import parts or stock data from a CSV string. For migrating data from legacy systems (Excel exports, old databases, etc.).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "csv_data": {"type": "string", "description": "CSV content with headers"},
                        "import_type": {"type": "string", "enum": ["parts", "stock", "machines"], "description": "What kind of data this CSV contains"},
                        "dry_run": {"type": "boolean", "description": "If true, validate but don't import (default: true)"}
                    },
                    "required": ["csv_data", "import_type"]
                }
            },
        ]

    # ── Tool Implementations ──

    def call_tool(self, name, arguments):
        self.logger.info(f"Tool call: {name}({json.dumps(arguments)[:200]})")
        try:
            method = getattr(self, f"_tool_{name}", None)
            if not method:
                return {"error": f"Unknown tool: {name}"}
            result = method(**arguments)
            return result
        except Exception as e:
            self.logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}

    def _tool_lookup_machine(self, machine_id):
        mid = machine_id.upper()
        # Resolve partial IDs
        if not mid.startswith("UGSI-"):
            for fam in FAMILIES:
                candidate = f"{fam['prefix']}-{mid.split('-')[-1].zfill(3)}"
                if any(mid in candidate for _ in [1]):
                    mid = candidate
                    break

        # Find machine info from family template
        machine = None
        for fam in FAMILIES:
            for i in range(1, fam["count"] + 1):
                full_id = f"{fam['prefix']}-{str(i).zfill(3)}"
                if full_id == mid or mid in full_id:
                    machine = {
                        "id": full_id, "family": fam["family"],
                        "model": fam["model"], "engine": fam["engine"],
                    }
                    mid = full_id
                    break
            if machine:
                break

        if not machine:
            return {"error": f"Machine '{machine_id}' not found. Use format UGSI-618-001."}

        # Find compatible parts
        family = machine["family"]
        all_parts = self.client.get_parts()
        categories = self.client.get_categories()
        compat = []
        for p in all_parts:
            text = f"{p.get('notes', '')} {p.get('description', '')} {p.get('name', '')}".lower()
            if family in text:
                stock = self.client.get_part_stock_summary(p["pk"])
                compat.append({
                    "name": p["name"], "IPN": p.get("IPN", ""),
                    "category": categories.get(p.get("category"), ""),
                    "in_stock": stock["total"],
                    "reorder_point": p.get("minimum_stock", 0),
                    "status": "OK" if stock["total"] > p.get("minimum_stock", 0) else
                             "LOW" if stock["total"] > 0 else "OUT",
                })

        return {
            "machine": machine,
            "compatible_parts": len(compat),
            "parts_in_stock": sum(1 for p in compat if p["status"] == "OK"),
            "parts_low": sum(1 for p in compat if p["status"] == "LOW"),
            "parts_out": sum(1 for p in compat if p["status"] == "OUT"),
            "parts": compat[:self.config["max_results"]],
        }

    def _tool_lookup_part(self, query, machine_family=None):
        parts = self.client.get_parts(search=query)
        categories = self.client.get_categories()
        results = []
        for p in parts[:self.config["max_results"]]:
            text = f"{p.get('notes', '')} {p.get('description', '')} {p.get('name', '')}".lower()
            if machine_family and machine_family not in text:
                continue
            stock = self.client.get_part_stock_summary(p["pk"])
            fits = [f for f in ["618", "900", "1200"] if f in text]
            results.append({
                "name": p["name"], "IPN": p.get("IPN", ""),
                "category": categories.get(p.get("category"), ""),
                "description": p.get("description", ""),
                "in_stock": stock["total"],
                "stock_locations": stock["items"],
                "reorder_point": p.get("minimum_stock", 0),
                "fits_machines": fits,
            })
        return {"query": query, "results_count": len(results), "parts": results}

    def _tool_check_stock(self, part_name=None, location=None):
        if part_name:
            parts = self.client.get_parts(search=part_name)
            if not parts:
                return {"error": f"No parts matching '{part_name}'"}
            results = []
            for p in parts[:10]:
                stock = self.client.get_part_stock_summary(p["pk"])
                results.append({
                    "name": p["name"], "IPN": p.get("IPN", ""),
                    "total": stock["total"],
                    "reorder_point": p.get("minimum_stock", 0),
                    "locations": stock["items"],
                    "needs_reorder": stock["total"] <= p.get("minimum_stock", 0),
                })
            return {"parts": results}
        else:
            # Overall status
            all_parts = self.client.get_parts()
            total_parts = len(all_parts)
            in_stock = 0
            out_of_stock = 0
            low_stock = 0
            for p in all_parts:
                stock = self.client.get_part_stock_summary(p["pk"])
                if stock["total"] == 0:
                    out_of_stock += 1
                elif stock["total"] <= p.get("minimum_stock", 0):
                    low_stock += 1
                else:
                    in_stock += 1
            return {
                "total_parts": total_parts,
                "in_stock": in_stock,
                "low_stock": low_stock,
                "out_of_stock": out_of_stock,
            }

    def _tool_adjust_stock(self, part_query, location, quantity, reason=None):
        if not self.config.get("enable_write_operations"):
            return {"error": "Write operations are disabled. Enable via set_config('enable_write_operations', true) or the control panel."}

        parts = self.client.get_parts(search=part_query)
        if not parts:
            return {"error": f"No parts matching '{part_query}'"}
        part = parts[0]

        locations = self.client.get_locations()
        loc_pk = None
        for pk, name in locations.items():
            if name.lower() == location.lower():
                loc_pk = pk
                break
        if loc_pk is None:
            return {"error": f"Location '{location}' not found. Available: {list(locations.values())}"}

        result = self.client.adjust_stock(part["pk"], loc_pk, quantity)
        self.logger.info(f"Stock adjusted: {part['name']} {quantity:+d} at {location} — {reason or 'no reason given'}")
        return {
            "part": part["name"],
            "location": location,
            "adjustment": quantity,
            "new_total": result["total"],
            "reason": reason,
        }

    def _tool_fleet_status(self, status=None, family=None, job=None):
        machines = []
        for fam in FAMILIES:
            if family and fam["family"] != family:
                continue
            for i in range(1, fam["count"] + 1):
                m = {
                    "id": f"{fam['prefix']}-{str(i).zfill(3)}",
                    "model": fam["model"],
                    "family": fam["family"],
                    "engine": fam["engine"],
                    "status": "Shop",  # Default — real status from localStorage in shop app
                }
                if status and m["status"] != status:
                    continue
                machines.append(m)

        summary = {
            "total": len(machines),
            "by_family": {},
        }
        for fam in FAMILIES:
            count = sum(1 for m in machines if m["family"] == fam["family"])
            if count > 0:
                summary["by_family"][fam["model"]] = count

        return {"summary": summary, "machines": machines}

    def _tool_low_stock_report(self, format="summary"):
        all_parts = self.client.get_parts()
        categories = self.client.get_categories()
        low = []
        for p in all_parts:
            rp = p.get("minimum_stock", 0)
            if rp <= 0:
                continue
            stock = self.client.get_part_stock_summary(p["pk"])
            if stock["total"] <= rp:
                low.append({
                    "name": p["name"], "IPN": p.get("IPN", ""),
                    "category": categories.get(p.get("category"), ""),
                    "in_stock": stock["total"],
                    "reorder_point": rp,
                    "shortfall": rp - stock["total"],
                })

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Part Name", "SKU", "Category", "In Stock", "Reorder Point", "Shortfall"])
            for item in low:
                writer.writerow([item["name"], item["IPN"], item["category"],
                                 item["in_stock"], item["reorder_point"], item["shortfall"]])
            return {"csv": output.getvalue(), "count": len(low)}

        return {"low_stock_count": len(low), "items": low}

    def _tool_inventory_snapshot(self):
        all_parts = self.client.get_parts()
        categories = self.client.get_categories()
        cat_counts = {}
        total_stock = 0
        out_count = 0
        for p in all_parts:
            cat = categories.get(p.get("category"), "Other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            stock = p.get("in_stock", 0)
            total_stock += stock
            if stock == 0:
                out_count += 1

        return {
            "total_parts": len(all_parts),
            "total_stock_items": total_stock,
            "out_of_stock": out_count,
            "categories": len(cat_counts),
            "top_categories": dict(sorted(cat_counts.items(), key=lambda x: -x[1])[:10]),
            "machines": sum(f["count"] for f in FAMILIES),
            "machine_families": {f["model"]: f["count"] for f in FAMILIES},
        }

    def _tool_system_health(self):
        health = self.client.health_check()
        health["config"] = {
            "dev_mode": self.config["dev_mode"],
            "write_ops": self.config["enable_write_operations"],
            "cache_ttl": self.config["cache_ttl_seconds"],
            "log_level": self.config["log_level"],
            "integrations_enabled": [
                k for k, v in self.config.get("integrations", {}).items()
                if v.get("enabled")
            ],
        }
        health["cache_entries"] = len(self.client._cache)
        return health

    def _tool_get_config(self, section=None):
        if section:
            if "." in section:
                parts = section.split(".")
                val = self.config
                for p in parts:
                    val = val.get(p, {}) if isinstance(val, dict) else None
                return {section: val}
            return {section: self.config.get(section)}
        # Return full config minus sensitive fields
        safe = {k: v for k, v in self.config.items()
                if "password" not in k.lower() and "secret" not in k.lower()}
        return safe

    def _tool_set_config(self, key, value):
        if "password" in key.lower() or "secret" in key.lower():
            return {"error": "Cannot set secrets via config tool. Use environment variables."}

        # Handle dotted keys (e.g. integrations.sharepoint.enabled)
        if "." in key:
            parts = key.split(".")
            target = self.config
            for p in parts[:-1]:
                if p not in target:
                    target[p] = {}
                target = target[p]
            target[parts[-1]] = value
        else:
            self.config[key] = value

        save_config(self.config)
        self.logger.info(f"Config updated: {key} = {value}")

        # Reload client if URL/user changed
        if key in ("inventree_url", "inventree_user"):
            self.client = InvenTreeClient(self.config)

        return {"updated": key, "value": value, "saved": True}

    def _tool_import_csv(self, csv_data, import_type, dry_run=True):
        if not self.config.get("enable_write_operations") and not dry_run:
            return {"error": "Write operations disabled. Enable first or use dry_run=true."}

        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)

        if not rows:
            return {"error": "No data rows found in CSV"}

        result = {
            "import_type": import_type,
            "dry_run": dry_run,
            "total_rows": len(rows),
            "columns_found": list(rows[0].keys()),
            "preview": rows[:5],
        }

        if import_type == "parts":
            required = {"name"}
            found = set(rows[0].keys())
            missing = required - found
            if missing:
                result["error"] = f"Missing required columns: {missing}"
                return result
            result["valid_rows"] = sum(1 for r in rows if r.get("name", "").strip())
            result["status"] = "ready" if not missing else "invalid"

        elif import_type == "stock":
            required = {"part", "quantity"}
            found = set(rows[0].keys())
            missing = required - found
            if missing:
                result["error"] = f"Missing required columns: {missing}"
                return result
            result["valid_rows"] = sum(1 for r in rows if r.get("part", "").strip())

        elif import_type == "machines":
            result["valid_rows"] = len(rows)

        if not dry_run and result.get("status") != "invalid":
            result["status"] = "import_not_yet_implemented"
            result["message"] = "CSV validation passed. Full import pipeline coming in v2."

        return result

    # ── MCP Protocol (stdio) ──

    def run_stdio(self):
        """Run as stdio MCP server for Claude Code."""
        self.logger.info("UGSI MCP Server starting (stdio mode)")

        # Send server info
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            method = msg.get("method", "")
            msg_id = msg.get("id")

            if method == "initialize":
                self._respond(msg_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "ugsi-mcelroy-shop",
                        "version": "1.0.0",
                        "description": "UGSI McElroy Parts Inventory & Fleet Management",
                    },
                })
            elif method == "notifications/initialized":
                pass  # No response needed
            elif method == "tools/list":
                self._respond(msg_id, {"tools": self.get_tools()})
            elif method == "tools/call":
                params = msg.get("params", {})
                name = params.get("name", "")
                args = params.get("arguments", {})
                result = self.call_tool(name, args)
                self._respond(msg_id, {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                })
            elif method == "ping":
                self._respond(msg_id, {})
            else:
                self._respond(msg_id, {"error": f"Unknown method: {method}"})

    def _respond(self, msg_id, result):
        response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main():
    server = UGSIServer()
    if "--http" in sys.argv:
        print(f"HTTP mode not yet implemented. Use stdio mode with Claude Code:")
        print(f"  claude mcp add ugsi-shop python3 -m mcp_server.server")
        sys.exit(1)
    else:
        server.run_stdio()


if __name__ == "__main__":
    main()
