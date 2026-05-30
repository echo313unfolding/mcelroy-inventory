#!/usr/bin/env python3
"""
Scrape McElroy parts data for 618, 900, and 1200 machine families.
Uses Playwright to navigate the McElroy Parts Finder and mcelroyparts.com.
"""

import json
import time
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "scraped_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# Machine families we care about
MACHINES = {
    "618": {
        "variants": ["Rolling 618", "TracStar 618", "Pit Bull 618"],
        "pipe_range": "6\" IPS to 18\" IPS",
        "pipe_od_range": "6.625\" to 18.000\"",
    },
    "900": {
        "variants": ["Rolling 900", "TracStar 900"],
        "pipe_range": "8\" IPS to 24\" IPS (some to 36\")",
        "pipe_od_range": "8.625\" to 24.000\"",
    },
    "1200": {
        "variants": ["TracStar 1200", "MegaMc 1648"],
        "pipe_range": "12\" IPS to 48\" IPS",
        "pipe_od_range": "12.750\" to 48.000\"",
    },
}


def scrape_parts_finder(page):
    """Scrape the official McElroy Parts Finder at fusion.mcelroy.com."""
    results = {}

    print("[1/3] Loading McElroy Parts Finder...")
    page.goto("https://fusion.mcelroy.com/parts/exec", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)

    # Get page content to understand structure
    content = page.content()
    title = page.title()
    print(f"  Page title: {title}")

    # Look for machine selection dropdowns or links
    # Try to find all links/options related to our machines
    links = page.query_selector_all("a")
    all_links = []
    for link in links:
        href = link.get_attribute("href") or ""
        text = (link.inner_text() or "").strip()
        if text and len(text) > 1:
            all_links.append({"text": text, "href": href})

    results["parts_finder_links"] = all_links
    print(f"  Found {len(all_links)} links on parts finder")

    # Look for form elements (dropdowns, search boxes)
    selects = page.query_selector_all("select")
    for sel in selects:
        name = sel.get_attribute("name") or sel.get_attribute("id") or "unknown"
        options = sel.query_selector_all("option")
        opt_texts = [o.inner_text().strip() for o in options if o.inner_text().strip()]
        results[f"select_{name}"] = opt_texts
        print(f"  Select '{name}': {len(opt_texts)} options")
        if len(opt_texts) <= 50:
            for o in opt_texts:
                print(f"    - {o}")

    # Look for any search input
    inputs = page.query_selector_all("input")
    for inp in inputs:
        itype = inp.get_attribute("type") or "text"
        iname = inp.get_attribute("name") or inp.get_attribute("id") or ""
        print(f"  Input: type={itype} name={iname}")

    # Try specific part number lookups for known McElroy part numbers
    # These are common 618 parts from manuals
    known_parts = [
        "1855602",  # 618 insert set
        "AT1807502",  # Referenced in search results
        "1821901",  # 618 manual reference
    ]

    for pn in known_parts:
        try:
            search_url = f"https://fusion.mcelroy.com/parts/exec?service=external/Home&sp=S{pn}"
            page.goto(search_url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(1)

            # Get all text content
            body_text = page.inner_text("body")
            results[f"part_{pn}"] = body_text[:3000]
            print(f"  Part {pn}: {len(body_text)} chars")

            # Look for part details, prices, descriptions
            tables = page.query_selector_all("table")
            for i, table in enumerate(tables):
                rows = table.query_selector_all("tr")
                table_data = []
                for row in rows:
                    cells = row.query_selector_all("td, th")
                    row_data = [c.inner_text().strip() for c in cells]
                    if any(row_data):
                        table_data.append(row_data)
                if table_data:
                    results[f"part_{pn}_table_{i}"] = table_data
                    print(f"    Table {i}: {len(table_data)} rows")
        except Exception as e:
            print(f"  Part {pn} lookup failed: {e}")

    return results


def scrape_mcelroyparts_store(page):
    """Scrape the mcelroyparts.com Shopify store."""
    results = {}

    print("\n[2/3] Loading mcelroyparts.com store...")

    # Get collections page
    page.goto("https://www.mcelroyparts.com/collections", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(3)

    # Get all collection links
    content = page.content()
    body_text = page.inner_text("body")
    results["collections_text"] = body_text[:5000]
    print(f"  Collections page: {len(body_text)} chars")

    links = page.query_selector_all("a")
    collection_links = []
    for link in links:
        href = link.get_attribute("href") or ""
        text = (link.inner_text() or "").strip()
        if "/collections/" in href and text and len(text) > 1:
            collection_links.append({"text": text, "href": href})

    results["collection_links"] = collection_links
    print(f"  Found {len(collection_links)} collection links")
    for cl in collection_links:
        print(f"    - {cl['text']}: {cl['href']}")

    # Now scrape each relevant collection
    target_collections = []
    for cl in collection_links:
        t = cl["text"].lower()
        h = cl["href"].lower()
        if any(kw in t or kw in h for kw in ["618", "900", "1200", "insert", "heater", "facer",
                                                "carriage", "hydraulic", "datalogger", "data-logger",
                                                "jaw", "blade", "clamp", "all-products", "all products"]):
            target_collections.append(cl)

    if not target_collections:
        # If no keyword matches, grab all collections
        target_collections = collection_links[:20]

    print(f"\n  Scraping {len(target_collections)} target collections...")

    for coll in target_collections:
        href = coll["href"]
        if not href.startswith("http"):
            href = f"https://www.mcelroyparts.com{href}"

        try:
            print(f"\n  Collection: {coll['text']}")
            page.goto(href, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)

            # Scroll to load lazy content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            products = []

            # Look for product cards/items
            # Common Shopify selectors
            product_selectors = [
                ".product-card", ".product-item", ".grid-product",
                "[data-product-card]", ".collection-product",
                ".product-grid-item", ".grid__item",
            ]

            product_elements = []
            for sel in product_selectors:
                found = page.query_selector_all(sel)
                if found:
                    product_elements = found
                    print(f"    Found {len(found)} products via '{sel}'")
                    break

            if not product_elements:
                # Fallback: look for product links
                all_links = page.query_selector_all("a[href*='/products/']")
                seen_hrefs = set()
                for link in all_links:
                    lhref = link.get_attribute("href") or ""
                    ltext = (link.inner_text() or "").strip()
                    if lhref not in seen_hrefs and ltext and len(ltext) > 2:
                        seen_hrefs.add(lhref)
                        products.append({
                            "name": ltext,
                            "url": lhref,
                        })
                print(f"    Found {len(products)} product links")
            else:
                for elem in product_elements:
                    name_el = elem.query_selector("h2, h3, .product-title, .product-card__title, .grid-product__title, a")
                    price_el = elem.query_selector(".price, .product-price, .money, .grid-product__price")
                    link_el = elem.query_selector("a[href*='/products/']")

                    name = name_el.inner_text().strip() if name_el else ""
                    price = price_el.inner_text().strip() if price_el else ""
                    url = link_el.get_attribute("href") if link_el else ""

                    if name:
                        products.append({
                            "name": name,
                            "price": price,
                            "url": url,
                        })

            coll_key = coll["text"].replace(" ", "_").lower()[:40]
            results[f"collection_{coll_key}"] = {
                "name": coll["text"],
                "url": href,
                "products": products,
            }

            # Also get the full page text for any table/list data
            body = page.inner_text("body")
            results[f"collection_{coll_key}_text"] = body[:5000]

        except Exception as e:
            print(f"    Error scraping {coll['text']}: {e}")

    return results


def scrape_machine_specs(page):
    """Scrape machine specification pages from mcelroy.com."""
    results = {}

    print("\n[3/3] Loading machine spec pages...")

    spec_urls = [
        ("TracStar 618", "https://www.mcelroy.com/productdetail.htm?class=TracStar+618"),
        ("Rolling 618", "https://www.mcelroy.com/productdetail.htm?class=Rolling+618"),
        ("Pit Bull 618", "https://www.mcelroy.com/en/productdetail.htm?class=Pit+Bull+618"),
        ("TracStar 900", "https://www.mcelroy.com/productdetail.htm?class=TracStar+900"),
        ("TracStar 1200", "https://www.mcelroy.com/productdetail.htm?class=TracStar+1200"),
    ]

    for name, url in spec_urls:
        try:
            print(f"  {name}...")
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)

            body = page.inner_text("body")
            results[name] = body[:5000]

            # Look for spec tables
            tables = page.query_selector_all("table")
            for i, table in enumerate(tables):
                rows = table.query_selector_all("tr")
                table_data = []
                for row in rows:
                    cells = row.query_selector_all("td, th")
                    row_data = [c.inner_text().strip() for c in cells]
                    if any(row_data):
                        table_data.append(row_data)
                if table_data:
                    results[f"{name}_table_{i}"] = table_data

            # Look for downloadable PDFs (manuals, parts breakdowns)
            pdf_links = page.query_selector_all("a[href$='.pdf']")
            pdfs = []
            for pdf in pdf_links:
                pdfs.append({
                    "text": (pdf.inner_text() or "").strip(),
                    "href": pdf.get_attribute("href"),
                })
            if pdfs:
                results[f"{name}_pdfs"] = pdfs
                print(f"    Found {len(pdfs)} PDF links")

            print(f"    {len(body)} chars of content")
        except Exception as e:
            print(f"    Error: {e}")

    return results


def scrape_parts_breakdown_pages(page):
    """Scrape parts breakdown pages from mcelroyparts.com."""
    results = {}

    print("\n[BONUS] Checking parts breakdown pages...")

    breakdown_urls = [
        ("618", "https://www.mcelroyparts.com/pages/rolling-618-parts-breakdown"),
        ("618_tracstar", "https://www.mcelroyparts.com/pages/tracstar-618-parts-breakdown"),
        ("618_pitbull", "https://www.mcelroyparts.com/pages/pit-bull-618-parts-breakdown"),
        ("900", "https://www.mcelroyparts.com/pages/rolling-900-parts-breakdown"),
        ("900_tracstar", "https://www.mcelroyparts.com/pages/tracstar-900-parts-breakdown"),
        ("1200", "https://www.mcelroyparts.com/pages/tracstar-1200-parts-breakdown"),
        ("1200_megamc", "https://www.mcelroyparts.com/pages/megamc-1648-parts-breakdown"),
        ("inserts", "https://www.mcelroyparts.com/collections/machine-insert-sets"),
    ]

    for name, url in breakdown_urls:
        try:
            print(f"  {name}...")
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)

            body = page.inner_text("body")
            results[f"breakdown_{name}"] = body[:8000]

            # Get all links (they often link to sub-assembly pages)
            links = page.query_selector_all("a")
            part_links = []
            for link in links:
                href = link.get_attribute("href") or ""
                text = (link.inner_text() or "").strip()
                if text and len(text) > 2 and ("/products/" in href or "/collections/" in href or "/pages/" in href):
                    part_links.append({"text": text, "href": href})

            results[f"breakdown_{name}_links"] = part_links
            print(f"    {len(body)} chars, {len(part_links)} links")

            # Look for images with alt text (parts diagrams)
            imgs = page.query_selector_all("img")
            img_data = []
            for img in imgs:
                alt = img.get_attribute("alt") or ""
                src = img.get_attribute("src") or ""
                if alt and ("part" in alt.lower() or "breakdown" in alt.lower() or "assembly" in alt.lower()):
                    img_data.append({"alt": alt, "src": src})
            if img_data:
                results[f"breakdown_{name}_images"] = img_data

        except Exception as e:
            print(f"    Error: {e}")

    return results


def main():
    print("=" * 60)
    print("McElroy Parts Scraper for InvenTree Import")
    print("Machines: 618, 900, 1200 (all variants)")
    print("=" * 60)

    all_results = {"machines": MACHINES}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 1. Official parts finder
            all_results["parts_finder"] = scrape_parts_finder(page)
        except Exception as e:
            print(f"Parts finder failed: {e}")
            all_results["parts_finder"] = {"error": str(e)}

        try:
            # 2. Parts store
            all_results["parts_store"] = scrape_mcelroyparts_store(page)
        except Exception as e:
            print(f"Parts store failed: {e}")
            all_results["parts_store"] = {"error": str(e)}

        try:
            # 3. Machine specs
            all_results["machine_specs"] = scrape_machine_specs(page)
        except Exception as e:
            print(f"Machine specs failed: {e}")
            all_results["machine_specs"] = {"error": str(e)}

        try:
            # 4. Parts breakdowns
            all_results["parts_breakdowns"] = scrape_parts_breakdown_pages(page)
        except Exception as e:
            print(f"Parts breakdowns failed: {e}")
            all_results["parts_breakdowns"] = {"error": str(e)}

        browser.close()

    # Save results
    out_file = OUTPUT_DIR / "mcelroy_scrape_results.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Results saved to {out_file}")
    print(f"Total keys: {sum(len(v) if isinstance(v, dict) else 1 for v in all_results.values())}")

    return all_results


if __name__ == "__main__":
    main()
