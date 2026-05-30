"""
InvenTree API client — thin wrapper for the MCP server tools.

Handles auth, pagination, caching, and error handling.
Designed to be the single point of contact with InvenTree,
so swapping backends later (different ERP, flat files, etc.) means
replacing only this file.
"""
import time
import json
import urllib.request
import urllib.parse
import urllib.error
from .config import load_config, get_inventree_password


class InvenTreeClient:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.base_url = self.config["inventree_url"].rstrip("/")
        self.user = self.config["inventree_user"]
        self.token = None
        self.token_expires = 0
        self._cache = {}
        self._cache_ts = {}

    def _get_token(self):
        if self.token and time.time() < self.token_expires:
            return self.token
        url = self.base_url + "/api/user/token/"
        req = urllib.request.Request(url)
        cred = f"{self.user}:{get_inventree_password()}"
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(cred.encode()).decode())
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        self.token = data["token"]
        self.token_expires = time.time() + 3600  # refresh hourly
        return self.token

    def _api(self, endpoint, params=None, method="GET", body=None):
        token = self._get_token()
        url = self.base_url + "/api/" + endpoint.strip("/") + "/"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        if body:
            data = json.dumps(body).encode()
        else:
            data = None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Token {token}")
        req.add_header("Content-Type", "application/json")
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e.fp else ""
            raise RuntimeError(f"InvenTree API {e.code}: {body_text[:200]}")

    def _api_all(self, endpoint, params=None):
        """Paginated fetch — returns all results."""
        results = []
        offset = 0
        base_params = dict(params or {})
        while True:
            base_params["limit"] = 500
            base_params["offset"] = offset
            d = self._api(endpoint, base_params)
            items = d.get("results", d if isinstance(d, list) else [])
            results.extend(items)
            if not d.get("next") or not items:
                break
            offset += 500
        return results

    def _cached(self, key, fetch_fn, ttl=None):
        ttl = ttl or self.config["cache_ttl_seconds"]
        if key in self._cache and (time.time() - self._cache_ts.get(key, 0)) < ttl:
            return self._cache[key]
        result = fetch_fn()
        self._cache[key] = result
        self._cache_ts[key] = time.time()
        return result

    def clear_cache(self):
        self._cache.clear()
        self._cache_ts.clear()

    # ── High-level methods used by MCP tools ──

    def get_parts(self, search=None, category=None, limit=None):
        """Search parts catalog."""
        params = {}
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        if limit:
            params["limit"] = limit
            return self._api("part", params).get("results", [])
        return self._api_all("part", params)

    def get_part_by_ipn(self, ipn):
        """Look up a single part by internal part number."""
        results = self._api("part", {"IPN": ipn}).get("results", [])
        return results[0] if results else None

    def get_categories(self):
        """Get all part categories."""
        return self._cached("categories", lambda: {
            c["pk"]: c["name"] for c in self._api_all("part/category")
        })

    def get_locations(self):
        """Get all stock locations."""
        return self._cached("locations", lambda: {
            l["pk"]: l["name"] for l in self._api_all("stock/location")
        })

    def get_stock(self, part_pk=None, location=None):
        """Get stock items, optionally filtered by part or location."""
        params = {}
        if part_pk:
            params["part"] = part_pk
        if location:
            params["location"] = location
        return self._api_all("stock", params)

    def get_part_stock_summary(self, part_pk):
        """Get stock summary for a specific part."""
        items = self.get_stock(part_pk=part_pk)
        locations = self.get_locations()
        stock_items = []
        total = 0
        for s in items:
            qty = s.get("quantity", 0)
            total += qty
            loc_name = locations.get(s.get("location"), "Unassigned")
            stock_items.append({"location": loc_name, "quantity": qty, "pk": s["pk"]})
        return {"total": total, "items": stock_items}

    def adjust_stock(self, part_pk, location_pk, quantity_delta):
        """Add or remove stock. Returns new total."""
        existing = self._api("stock", {"part": part_pk, "location": location_pk})
        items = existing.get("results", [])

        if quantity_delta > 0:
            if items:
                new_qty = items[0]["quantity"] + quantity_delta
                self._api(f"stock/{items[0]['pk']}", method="PATCH",
                          body={"quantity": new_qty})
            else:
                self._api("stock", method="POST",
                          body={"part": part_pk, "quantity": quantity_delta,
                                "location": location_pk})
        elif quantity_delta < 0 and items:
            new_qty = max(0, items[0]["quantity"] + quantity_delta)
            self._api(f"stock/{items[0]['pk']}", method="PATCH",
                      body={"quantity": new_qty})

        self.clear_cache()
        return self.get_part_stock_summary(part_pk)

    def health_check(self):
        """Check if InvenTree is reachable."""
        try:
            self._get_token()
            return {"status": "ok", "url": self.base_url, "user": self.user}
        except Exception as e:
            return {"status": "error", "error": str(e), "url": self.base_url}
