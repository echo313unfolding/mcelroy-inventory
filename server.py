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
    db.commit()

    # Migrate: add qr_code columns if missing (v0.1 upgrade)
    for table, col in [("machines", "qr_code"), ("part_bins", "qr_code")]:
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT DEFAULT ''")
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

class ShopHandler(http.server.SimpleHTTPRequestHandler):

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
            db.close()
            self.send_error(404, f"Machine {machine_id} not found")
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
            allowed = {"bin", "stock_qty", "notes", "qr_code"}
            updates = {k: v for k, v in data.items() if k in allowed}
            if updates:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                values = list(updates.values()) + [part_pk]
                db.execute(f"UPDATE part_bins SET {set_clause} WHERE part_pk = ?", values)
        else:
            db.execute(
                "INSERT INTO part_bins (part_pk, bin, stock_qty, notes, qr_code) VALUES (?, ?, ?, ?, ?)",
                (part_pk, data.get("bin", ""), data.get("stock_qty", 0), data.get("notes", ""), data.get("qr_code", "")),
            )
        db.commit()
        row = db.execute("SELECT * FROM part_bins WHERE part_pk = ?", (part_pk,)).fetchone()
        db.close()
        self._json_response(dict(row))

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
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
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
