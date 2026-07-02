#!/usr/bin/env python3
"""
UGSI McElroy Shop — Lightweight Server

Single-file Python server for the shop app. No external dependencies.
Uses SQLite for fleet/stock persistence, serves the shop HTML + parts JSON.

Usage:
    python3 server.py              # Start on port 8080
    python3 server.py --port 9000  # Custom port

Requirements: Python 3.8+ (install from Microsoft Store if needed)
"""

import http.server
import json
import os
import re
import sqlite3
import sys
import threading
import urllib.parse
from pathlib import Path

PORT = 8080
DB_PATH = "shop.db"
SHOP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop")

# Machine families — same as the shop HTML
FAMILIES = [
    {"family": "618", "model": "TracStar 618", "count": 20, "engine": "Kubota D1105", "prefix": "UGSI-618"},
    {"family": "900", "model": "TracStar 900", "count": 12, "engine": "Kubota V2403", "prefix": "UGSI-900"},
    {"family": "1200", "model": "TracStar 1200", "count": 4, "engine": "Kubota V3307", "prefix": "UGSI-1200"},
]

# ============================================================
# DATABASE
# ============================================================

def get_db():
    """Thread-local database connection."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init_db():
    """Create tables and seed fleet data on first run."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id TEXT PRIMARY KEY,
            family TEXT NOT NULL,
            model TEXT NOT NULL,
            engine_type TEXT DEFAULT '',
            serial TEXT DEFAULT '',
            engine_serial TEXT DEFAULT '',
            hours TEXT DEFAULT '',
            status TEXT DEFAULT 'Shop',
            job TEXT DEFAULT '',
            location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            qr_code TEXT DEFAULT ''
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS part_bins (
            part_pk INTEGER PRIMARY KEY,
            bin TEXT DEFAULT '',
            stock_qty REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            qr_code TEXT DEFAULT ''
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS repair_orders (
            id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL,
            date_opened TEXT DEFAULT '',
            date_closed TEXT DEFAULT '',
            repair_type TEXT DEFAULT '',
            status TEXT DEFAULT 'Draft',
            complaint TEXT DEFAULT '',
            work_performed TEXT DEFAULT '',
            labor_hours REAL DEFAULT 0,
            labor_rate REAL DEFAULT 110,
            outside_hours REAL DEFAULT 0,
            outside_rate REAL DEFAULT 150,
            constraint_notes TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS repair_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            part_pk INTEGER DEFAULT 0,
            part_name TEXT DEFAULT '',
            part_ipn TEXT DEFAULT '',
            qty REAL DEFAULT 1,
            unit_cost REAL DEFAULT 0,
            item_type TEXT DEFAULT 'part'
        )
    """)
    db.commit()

    # Migrate: add columns if missing
    migrations = [
        ("machines", "qr_code", "TEXT DEFAULT ''"),
        ("part_bins", "qr_code", "TEXT DEFAULT ''"),
        ("part_bins", "fits", "TEXT DEFAULT ''"),
    ]
    for table, col, coltype in migrations:
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
            db.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Seed machines if empty
    count = db.execute("SELECT COUNT(*) FROM machines").fetchone()[0]
    if count == 0:
        print("  Seeding 36 machines...")
        for fam in FAMILIES:
            for i in range(1, fam["count"] + 1):
                machine_id = f"{fam['prefix']}-{str(i).zfill(3)}"
                db.execute(
                    "INSERT INTO machines (id, family, model, engine_type, status) VALUES (?, ?, ?, ?, ?)",
                    (machine_id, fam["family"], fam["model"], fam["engine"], "Shop"),
                )
        db.commit()
        print(f"  Seeded {db.execute('SELECT COUNT(*) FROM machines').fetchone()[0]} machines")

    db.close()


# ============================================================
# HTTP HANDLER
# ============================================================

class ShopHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # Root → redirect to shop
        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/shop/")
            self.end_headers()
            return

        # API endpoints
        if path == "/api/health":
            return self._json_response({"status": "ok", "server": "ugsi-lite"})

        if path == "/api/fleet":
            return self._get_fleet()

        if path.startswith("/api/fleet/"):
            machine_id = urllib.parse.unquote(path[len("/api/fleet/"):].rstrip("/"))
            return self._get_machine(machine_id)

        if path == "/api/parts":
            return self._serve_file(os.path.join(SHOP_DIR, "parts_data.json"), "application/json")

        if path == "/api/bins":
            return self._get_bins()

        if path.startswith("/api/bins/"):
            part_pk = path[len("/api/bins/"):].rstrip("/")
            return self._get_bin(part_pk)

        if path == "/api/repairs":
            return self._get_repairs()

        if path.startswith("/api/repairs/") and "/items" not in path:
            order_id = urllib.parse.unquote(path[len("/api/repairs/"):].rstrip("/"))
            return self._get_repair(order_id)

        if path.startswith("/api/repairs/") and path.endswith("/items"):
            order_id = urllib.parse.unquote(path[len("/api/repairs/"):-len("/items")])
            return self._get_repair_items(order_id)

        # Static files from shop/
        if path.startswith("/shop/"):
            rel = path[len("/shop/"):]
            if rel == "" or rel == "/":
                rel = "index.html"
            filepath = os.path.join(SHOP_DIR, rel)
            if os.path.isfile(filepath):
                ctype = self._guess_type(filepath)
                return self._serve_file(filepath, ctype)
            self.send_error(404)
            return

        self.send_error(404)

    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/api/fleet/"):
            machine_id = urllib.parse.unquote(path[len("/api/fleet/"):].rstrip("/"))
            body = self._read_body()
            if body is None:
                return
            return self._update_machine(machine_id, body)

        if path.startswith("/api/bins/"):
            part_pk = path[len("/api/bins/"):].rstrip("/")
            body = self._read_body()
            if body is None:
                return
            return self._update_bin(part_pk, body)

        if path.startswith("/api/repairs/") and path.endswith("/items"):
            order_id = urllib.parse.unquote(path[len("/api/repairs/"):-len("/items")])
            body = self._read_body()
            if body is None:
                return
            return self._add_repair_item(order_id, body)

        if path.startswith("/api/repairs/"):
            order_id = urllib.parse.unquote(path[len("/api/repairs/"):].rstrip("/"))
            body = self._read_body()
            if body is None:
                return
            return self._update_repair(order_id, body)

        self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/repairs":
            body = self._read_body()
            if body is None:
                return
            return self._create_repair(body)
        if path == "/api/auto-tag-machines":
            return self._auto_tag_machines()
        self.send_error(404)

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/api/fleet/"):
            machine_id = urllib.parse.unquote(path[len("/api/fleet/"):].rstrip("/"))
            return self._delete_machine(machine_id)

        if path.startswith("/api/repair-items/"):
            item_id = path[len("/api/repair-items/"):].rstrip("/")
            return self._delete_repair_item(item_id)

        if path.startswith("/api/repairs/"):
            order_id = urllib.parse.unquote(path[len("/api/repairs/"):].rstrip("/"))
            return self._delete_repair(order_id)

        self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ---- API handlers ----

    def _get_fleet(self):
        db = get_db()
        rows = db.execute("SELECT * FROM machines ORDER BY id").fetchall()
        db.close()
        machines = {row["id"]: dict(row) for row in rows}
        self._json_response(machines)

    def _get_machine(self, machine_id):
        db = get_db()
        row = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
        db.close()
        if row:
            self._json_response(dict(row))
        else:
            self.send_error(404, f"Machine {machine_id} not found")

    def _update_machine(self, machine_id, data):
        db = get_db()
        row = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()

        if not row:
            # Create new machine (upsert)
            family = data.get("family", machine_id.split("-")[1] if "-" in machine_id else "")
            fam_info = next((f for f in FAMILIES if f["family"] == family), None)
            model = data.get("model", fam_info["model"] if fam_info else "")
            engine = data.get("engine_type", fam_info["engine"] if fam_info else "")
            db.execute(
                "INSERT INTO machines (id, family, model, engine_type, serial, engine_serial, hours, status, job, location, notes, qr_code) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (machine_id, family, model, engine,
                 data.get("serial", ""), data.get("engine_serial", ""),
                 data.get("hours", ""), data.get("status", "Shop"),
                 data.get("job", ""), data.get("location", ""),
                 data.get("notes", ""), data.get("qr_code", "")),
            )
            db.commit()
            row = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
            db.close()
            self._json_response(dict(row))
            return

        # Update only provided fields
        allowed = {"serial", "engine_serial", "hours", "status", "job", "location", "notes", "qr_code"}
        updates = {k: v for k, v in data.items() if k in allowed}
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [machine_id]
            db.execute(f"UPDATE machines SET {set_clause} WHERE id = ?", values)
            db.commit()

        row = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
        db.close()
        self._json_response(dict(row))

    def _delete_machine(self, machine_id):
        db = get_db()
        row = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
        if not row:
            db.close()
            self.send_error(404, f"Machine {machine_id} not found")
            return
        db.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
        db.commit()
        db.close()
        self._json_response({"deleted": machine_id})

    # ---- Bin handlers ----

    def _get_bins(self):
        db = get_db()
        rows = db.execute("SELECT * FROM part_bins").fetchall()
        db.close()
        bins = {str(row["part_pk"]): dict(row) for row in rows}
        self._json_response(bins)

    def _get_bin(self, part_pk):
        db = get_db()
        row = db.execute("SELECT * FROM part_bins WHERE part_pk = ?", (part_pk,)).fetchone()
        db.close()
        if row:
            self._json_response(dict(row))
        else:
            self._json_response({"part_pk": int(part_pk), "bin": "", "stock_qty": 0, "notes": ""})

    def _update_bin(self, part_pk, data):
        db = get_db()
        row = db.execute("SELECT * FROM part_bins WHERE part_pk = ?", (part_pk,)).fetchone()
        if row:
            allowed = {"bin", "stock_qty", "notes", "qr_code", "fits"}
            updates = {k: v for k, v in data.items() if k in allowed}
            if updates:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                values = list(updates.values()) + [part_pk]
                db.execute(f"UPDATE part_bins SET {set_clause} WHERE part_pk = ?", values)
        else:
            db.execute(
                "INSERT INTO part_bins (part_pk, bin, stock_qty, notes, qr_code, fits) VALUES (?, ?, ?, ?, ?, ?)",
                (part_pk, data.get("bin", ""), data.get("stock_qty", 0), data.get("notes", ""), data.get("qr_code", ""), data.get("fits", "")),
            )
        db.commit()
        row = db.execute("SELECT * FROM part_bins WHERE part_pk = ?", (part_pk,)).fetchone()
        db.close()
        self._json_response(dict(row))

    # ---- Repair Order handlers ----

    def _get_repairs(self):
        db = get_db()
        rows = db.execute("SELECT * FROM repair_orders ORDER BY date_opened DESC").fetchall()
        db.close()
        self._json_response([dict(r) for r in rows])

    def _get_repair(self, order_id):
        db = get_db()
        row = db.execute("SELECT * FROM repair_orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            db.close()
            self.send_error(404, f"Repair order {order_id} not found")
            return
        order = dict(row)
        items = db.execute("SELECT * FROM repair_order_items WHERE order_id = ?", (order_id,)).fetchall()
        db.close()
        order["items"] = [dict(i) for i in items]
        self._json_response(order)

    def _get_repair_items(self, order_id):
        db = get_db()
        rows = db.execute("SELECT * FROM repair_order_items WHERE order_id = ?", (order_id,)).fetchall()
        db.close()
        self._json_response([dict(r) for r in rows])

    def _create_repair(self, data):
        db = get_db()
        order_id = data.get("id", f"RO-{int(__import__('time').time())}")
        db.execute(
            "INSERT INTO repair_orders (id, machine_id, date_opened, repair_type, status, complaint, labor_rate, outside_rate) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, data.get("machine_id", ""), data.get("date_opened", ""),
             data.get("repair_type", ""), data.get("status", "Draft"),
             data.get("complaint", ""), data.get("labor_rate", 110), data.get("outside_rate", 150)),
        )
        db.commit()
        row = db.execute("SELECT * FROM repair_orders WHERE id = ?", (order_id,)).fetchone()
        db.close()
        self._json_response(dict(row))

    def _update_repair(self, order_id, data):
        db = get_db()
        allowed = {"machine_id", "date_opened", "date_closed", "repair_type", "status",
                    "complaint", "work_performed", "labor_hours", "labor_rate",
                    "outside_hours", "outside_rate", "constraint_notes", "notes"}
        updates = {k: v for k, v in data.items() if k in allowed}
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [order_id]
            db.execute(f"UPDATE repair_orders SET {set_clause} WHERE id = ?", values)
            db.commit()
        row = db.execute("SELECT * FROM repair_orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            db.close()
            self.send_error(404)
            return
        order = dict(row)
        items = db.execute("SELECT * FROM repair_order_items WHERE order_id = ?", (order_id,)).fetchall()
        db.close()
        order["items"] = [dict(i) for i in items]
        self._json_response(order)

    def _add_repair_item(self, order_id, data):
        db = get_db()
        db.execute(
            "INSERT INTO repair_order_items (order_id, part_pk, part_name, part_ipn, qty, unit_cost, item_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (order_id, data.get("part_pk", 0), data.get("part_name", ""),
             data.get("part_ipn", ""), data.get("qty", 1),
             data.get("unit_cost", 0), data.get("item_type", "part")),
        )
        db.commit()
        items = db.execute("SELECT * FROM repair_order_items WHERE order_id = ?", (order_id,)).fetchall()
        db.close()
        self._json_response([dict(i) for i in items])

    def _delete_repair_item(self, item_id):
        db = get_db()
        db.execute("DELETE FROM repair_order_items WHERE id = ?", (item_id,))
        db.commit()
        db.close()
        self._json_response({"deleted": item_id})

    def _delete_repair(self, order_id):
        db = get_db()
        db.execute("DELETE FROM repair_order_items WHERE order_id = ?", (order_id,))
        db.execute("DELETE FROM repair_orders WHERE id = ?", (order_id,))
        db.commit()
        db.close()
        self._json_response({"deleted": order_id})

    # ---- Auto-tag machine compatibility ----

    def _auto_tag_machines(self):
        """Auto-populate 'fits' field on parts using text matching and IPN prefix heuristics."""
        parts_file = os.path.join(SHOP_DIR, "parts_data.json")
        if not os.path.isfile(parts_file):
            return self._json_response({"error": "parts_data.json not found"}, 400)

        with open(parts_file) as f:
            pdata = json.load(f)

        parts = pdata.get("parts", [])
        cats = pdata.get("categories", {})

        # Universal categories — fit ALL machines
        universal_cats = {29, 30, 31, 32, 33, 34, 27, 28, 37}  # Consumables, Filters, Heater Supplies, Fusion, Safety, Accessories, DataLogger, Tensile

        tagged_count = 0
        skipped_count = 0
        db = get_db()

        for p in parts:
            pk = p["pk"]
            # Skip if already has a fits value
            row = db.execute("SELECT fits FROM part_bins WHERE part_pk = ?", (pk,)).fetchone()
            if row and row["fits"]:
                skipped_count += 1
                continue

            machines = set()
            name = p.get("name", "")
            desc = p.get("description", "")
            ipn = p.get("IPN", "")
            cat = p.get("category", 0)
            text = f"{name} {desc}".lower()

            # Strategy 1: Text match (highest confidence)
            if re.search(r'(?:^|[^0-9])618(?:[^0-9]|$)', text):
                machines.add("618")
            if re.search(r'(?:^|[^0-9])900(?:[^0-9]|$)', text):
                machines.add("900")
            if re.search(r'(?:^|[^0-9])1200(?:[^0-9]|$)', text):
                machines.add("1200")
            # 412 is 618 family sub-model
            if re.search(r'(?:^|[^0-9])412(?:[^0-9]|$)', text):
                machines.add("618")

            # Strategy 2: IPN prefix (good confidence)
            ipn_upper = ipn.upper()
            if ipn_upper.startswith("T1") and not ipn_upper.startswith("T12"):
                machines.add("618")
            if ipn_upper.startswith("T9"):
                machines.add("900")
            if ipn_upper.startswith("T4"):
                machines.add("1200")

            # Strategy 3: Universal categories → all machines
            if cat in universal_cats:
                machines = {"618", "900", "1200"}

            if not machines:
                continue

            fits = ",".join(sorted(machines))
            # Upsert into part_bins
            if row is not None:
                db.execute("UPDATE part_bins SET fits = ? WHERE part_pk = ?", (fits, pk))
            else:
                db.execute(
                    "INSERT INTO part_bins (part_pk, bin, stock_qty, notes, qr_code, fits) VALUES (?, '', 0, '', '', ?)",
                    (pk, fits),
                )
            tagged_count += 1

        db.commit()
        db.close()
        self._json_response({
            "tagged": tagged_count,
            "skipped_existing": skipped_count,
            "total_parts": len(parts),
        })

    # ---- Helpers ----

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filepath, content_type):
        with open(filepath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self.send_error(400, "Empty request body")
            return None
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return None

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _guess_type(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(ext, "application/octet-stream")

    def log_message(self, format, *args):
        # Quieter logging — skip static file requests
        msg = format % args
        if "/shop/" in msg and "api" not in msg:
            return
        print(f"  {msg}")


# ============================================================
# MAIN
# ============================================================

def main():
    port = PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    print("=" * 50)
    print("  Shop App — Server")
    print("=" * 50)
    print(f"  Database: {os.path.abspath(DB_PATH)}")

    # Check shop directory
    if not os.path.isdir(SHOP_DIR):
        print(f"\n  ERROR: Shop directory not found: {SHOP_DIR}")
        print(f"  Make sure index.html is in the 'shop' folder.")
        input("\n  Press Enter to exit...")
        sys.exit(1)

    # Check parts data
    parts_file = os.path.join(SHOP_DIR, "parts_data.json")
    if os.path.isfile(parts_file):
        size_mb = os.path.getsize(parts_file) / 1024 / 1024
        print(f"  Parts data: {size_mb:.1f} MB")
    else:
        print(f"  WARNING: No parts_data.json found — parts won't load")

    # Init database
    init_db()

    # Start server
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), ShopHandler)
    print(f"\n  Shop app: http://localhost:{port}/shop/")

    # Show local IP for iPhone access
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"  iPhone:   http://{ip}:{port}/shop/")
    except Exception:
        print(f"  iPhone:   http://<this-computer-ip>:{port}/shop/")

    print(f"\n  Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
