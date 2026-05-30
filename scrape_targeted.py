#!/usr/bin/env python3
"""
Targeted McElroy parts scraper — only the 618, 900, 1200 collections + inserts.
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "scraped_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# Only the collections we actually need
TARGETS = [
    # 618 family
    ("pitbull_618", "/collections/pitbull-618"),
    ("rolling_618", "/collections/rolling-618"),
    ("rolling_618_electric", "/collections/rolling-618-electric"),
    ("tracstar_618", "/collections/tracstar-618-fusion-machine"),
    ("tracstar_618_auto", "/collections/tracstar-618-fusion-machine-automated"),
    # 900 family
    ("tracstar_900_ulsd", "/collections/tracstar-900-fusion-machine"),
    ("tracstar_900_hsd", "/collections/tracstar-900-fusion-machine-high-sulfur-diesel-engine"),
    ("tracstar_900_ulsd_auto", "/collections/tracstar-900-fusion-machine-ultra-low-sulfur-diesel-engine-automated"),
    ("tracstar_900_hsd_auto", "/collections/tracstar-900-fusion-machine-high-sulfur-diesel-engine-automated"),
    # 1200 family
    ("tracstar_1200_ulsd", "/collections/tracstar-1200-fusion-machine"),
    ("tracstar_1200_hsd", "/collections/tracstar-1200-fusion-machine-high-sulfur-diesel-engine"),
    ("tracstar_1200_auto", "/collections/tracstar-1200-fusion-machine-automated"),
    ("megamc_1648", "/collections/megamc-1648-fusion-machine"),
    # Shared components
    ("insert_sets", "/collections/machine-insert-sets"),
    ("facer_blades_618", "/collections/618-facer-blades"),
    ("facer_blades_900", "/collections/tracstar-900-megamc-1648-facer-blades"),
    ("heaters", "/collections/heaters"),
    ("dataloggers", "/collections/datalogger"),
    ("hydraulic_power", "/collections/hydraulic-power-units"),
    # Parts breakdowns
    ("breakdown_618", "/pages/rolling-618-parts-breakdown"),
    ("breakdown_618_ts", "/pages/tracstar-618-parts-breakdown"),
    ("breakdown_618_pb", "/pages/pit-bull-618-parts-breakdown"),
    ("breakdown_900", "/pages/tracstar-900-parts-breakdown"),
    ("breakdown_1200", "/pages/tracstar-1200-parts-breakdown"),
    ("breakdown_megamc", "/pages/megamc-1648-parts-breakdown"),
]

BASE = "https://www.mcelroyparts.com"


def scrape_collection(page, name, path):
    """Scrape a single collection page."""
    url = f"{BASE}{path}"
    result = {"name": name, "url": url, "products": [], "links": []}

    page.goto(url, timeout=20000)
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    time.sleep(2)

    # Scroll to trigger lazy loading
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # Get products
    items = page.query_selector_all(".grid__item")
    for item in items:
        product = {}

        # Title
        title_el = item.query_selector(".grid-product__title, .product-card__title, h2, h3")
        if title_el:
            product["name"] = title_el.inner_text().strip()

        # Price
        price_el = item.query_selector(".grid-product__price, .price, .money")
        if price_el:
            product["price"] = price_el.inner_text().strip()

        # Link
        link_el = item.query_selector("a[href*='/products/']")
        if link_el:
            product["url"] = link_el.get_attribute("href")

        # Image alt (often has part number)
        img_el = item.query_selector("img")
        if img_el:
            product["image_alt"] = (img_el.get_attribute("alt") or "").strip()

        if product.get("name"):
            result["products"].append(product)

    # Also grab all links for parts breakdown pages
    all_links = page.query_selector_all("a")
    for link in all_links:
        href = link.get_attribute("href") or ""
        text = (link.inner_text() or "").strip()
        if text and len(text) > 2 and ("/products/" in href or "/pages/" in href):
            if {"text": text, "href": href} not in result["links"]:
                result["links"].append({"text": text, "href": href})

    # Get page body text for breakdown pages
    if "/pages/" in path:
        result["body_text"] = page.inner_text("body")[:10000]

    return result


def scrape_product_detail(page, url):
    """Scrape a single product page for part numbers and details."""
    if not url.startswith("http"):
        url = f"{BASE}{url}"

    result = {}
    page.goto(url, timeout=15000)
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    time.sleep(1)

    # Product title
    title_el = page.query_selector("h1, .product-single__title")
    if title_el:
        result["title"] = title_el.inner_text().strip()

    # SKU
    sku_el = page.query_selector(".product-single__sku, [data-product-sku], .sku")
    if sku_el:
        result["sku"] = sku_el.inner_text().strip()

    # Price
    price_el = page.query_selector(".product__price, .price, .money")
    if price_el:
        result["price"] = price_el.inner_text().strip()

    # Description
    desc_el = page.query_selector(".product-single__description, .product-description, .rte")
    if desc_el:
        result["description"] = desc_el.inner_text().strip()[:1000]

    # Variants (different sizes/options)
    variant_els = page.query_selector_all("select option, .swatch-element label, [data-value]")
    variants = []
    for v in variant_els:
        vtext = (v.inner_text() or v.get_attribute("data-value") or "").strip()
        if vtext and vtext not in variants:
            variants.append(vtext)
    if variants:
        result["variants"] = variants

    # Try to get structured product data from JSON-LD or Shopify product JSON
    try:
        product_json = page.evaluate("""
            () => {
                // Shopify stores often have product data in window
                if (typeof meta !== 'undefined' && meta.product) return meta.product;
                // Try JSON-LD
                const ld = document.querySelector('script[type="application/ld+json"]');
                if (ld) return JSON.parse(ld.textContent);
                return null;
            }
        """)
        if product_json:
            result["structured_data"] = product_json
    except:
        pass

    return result


def main():
    print("=" * 60)
    print("Targeted McElroy Parts Scraper")
    print(f"Targets: {len(TARGETS)} pages")
    print("=" * 60)

    all_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = ctx.new_page()

        # Scrape all target collections/pages
        for name, path in TARGETS:
            try:
                print(f"  [{name}] ", end="", flush=True)
                data = scrape_collection(page, name, path)
                all_data[name] = data
                n_products = len(data["products"])
                n_links = len(data["links"])
                print(f"{n_products} products, {n_links} links")
            except Exception as e:
                print(f"ERROR: {e}")
                all_data[name] = {"error": str(e)}

        # Now drill into product detail pages for the first few products
        # from each key collection to get part numbers, SKUs, prices
        detail_targets = []
        for key in ["pitbull_618", "rolling_618", "tracstar_618",
                     "tracstar_900_ulsd", "tracstar_1200_ulsd",
                     "insert_sets", "dataloggers"]:
            if key in all_data and "products" in all_data[key]:
                for prod in all_data[key]["products"][:10]:  # First 10 from each
                    if prod.get("url"):
                        detail_targets.append((key, prod["url"], prod.get("name", "")))

        print(f"\nScraping {len(detail_targets)} product detail pages...")
        product_details = {}
        for coll_key, url, prod_name in detail_targets:
            try:
                print(f"  [{coll_key}] {prod_name[:40]}... ", end="", flush=True)
                detail = scrape_product_detail(page, url)
                detail["collection"] = coll_key
                product_details[url] = detail
                sku = detail.get("sku", "no-sku")
                print(f"SKU: {sku}")
            except Exception as e:
                print(f"ERROR: {e}")

        all_data["product_details"] = product_details

        browser.close()

    # Save
    out_file = OUTPUT_DIR / "mcelroy_targeted.json"
    with open(out_file, "w") as f:
        json.dump(all_data, f, indent=2, default=str)

    # Summary
    total_products = sum(
        len(v.get("products", []))
        for k, v in all_data.items()
        if isinstance(v, dict) and k != "product_details"
    )
    total_details = len(product_details)

    print(f"\n{'=' * 60}")
    print(f"Results saved to {out_file}")
    print(f"Total collection products: {total_products}")
    print(f"Product details scraped: {total_details}")
    print(f"File size: {out_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
