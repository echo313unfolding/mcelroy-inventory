#!/usr/bin/env python3
"""
Scrape the OFFICIAL McElroy Parts Finder at fusion.mcelroy.com
and the McElroy catalog PDF. This is where the real parts data lives.
"""

import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "scraped_data"
OUTPUT_DIR.mkdir(exist_ok=True)


def scrape_official_parts_finder(page):
    """Navigate the official McElroy parts finder at fusion.mcelroy.com."""
    results = {}

    print("=== Official McElroy Parts Finder ===")
    page.goto("https://fusion.mcelroy.com/parts/exec", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(3)

    # Dump full page HTML structure for analysis
    html = page.content()
    results["home_html_length"] = len(html)

    # Get full body text
    body = page.inner_text("body")
    results["home_body"] = body[:10000]
    print(f"  Home page: {len(body)} chars")
    print(f"  Body preview: {body[:500]}")

    # Find all selects, forms, iframes
    frames = page.frames
    print(f"  Frames: {len(frames)}")
    for f in frames:
        print(f"    Frame: {f.name} url={f.url[:80]}")

    # Check for iframes (parts finder might be in an iframe)
    iframes = page.query_selector_all("iframe")
    for iframe in iframes:
        src = iframe.get_attribute("src") or ""
        print(f"  iframe src: {src}")

    # Get ALL links
    links = page.query_selector_all("a")
    all_links = []
    for link in links:
        href = link.get_attribute("href") or ""
        text = (link.inner_text() or "").strip()
        if text and len(text) > 1:
            all_links.append({"text": text, "href": href})
    results["all_links"] = all_links

    # Look for machine-related links
    machine_links = [l for l in all_links if any(
        kw in l["text"].lower() or kw in l["href"].lower()
        for kw in ["618", "900", "1200", "tracstar", "rolling", "pitbull", "pit bull", "megamc"]
    )]
    results["machine_links"] = machine_links
    print(f"\n  Machine links: {len(machine_links)}")
    for ml in machine_links:
        print(f"    {ml['text']}: {ml['href']}")

    # Try to navigate machine-specific pages
    # The parts finder uses URL params like sp=S{part_number}
    # Let's try the main machine category pages
    machine_pages = {
        "618": "https://fusion.mcelroy.com/parts/exec?service=external/Home&sp=S618",
        "900": "https://fusion.mcelroy.com/parts/exec?service=external/Home&sp=S900",
        "1200": "https://fusion.mcelroy.com/parts/exec?service=external/Home&sp=S1200",
    }

    for machine, url in machine_pages.items():
        try:
            print(f"\n  Trying {machine} page...")
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            body = page.inner_text("body")
            results[f"machine_{machine}"] = body[:5000]
            print(f"    {len(body)} chars")
            print(f"    Preview: {body[:300]}")
        except Exception as e:
            print(f"    Error: {e}")

    return results


def scrape_mcelroyparts_collections_js(page):
    """Scrape mcelroyparts.com with longer JS wait for Shopify rendering."""
    results = {}

    print("\n=== mcelroyparts.com (with JS wait) ===")

    # These collection slugs were confirmed working in the first scraper
    collections = {
        "pitbull_618": "pitbull-618",
        "rolling_618": "rolling-618",
        "tracstar_618": "tracstar-618-fusion-machine",
        "tracstar_900": "tracstar-900-fusion-machine",
        "tracstar_1200": "tracstar-1200-fusion-machine",
        "insert_sets": "machine-insert-sets",
        "datalogger": "datalogger",
        "heater_plates": "heater-plates",
        "facer_blades": "618-facer-blades",
    }

    for name, slug in collections.items():
        url = f"https://www.mcelroyparts.com/collections/{slug}"
        try:
            print(f"\n  [{name}] Loading {slug}...")
            page.goto(url, timeout=20000)

            # Wait for Shopify to render - try multiple strategies
            try:
                page.wait_for_selector(".grid__item, .grid-product, .collection-products", timeout=8000)
            except:
                pass

            time.sleep(3)

            # Scroll and wait
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            # Try getting products with various selectors
            products = []
            for selector in [".grid__item", ".grid-product", ".product-card",
                             "[data-product-id]", ".collection-product", ".product-grid-item"]:
                items = page.query_selector_all(selector)
                if items:
                    print(f"    Found {len(items)} items via '{selector}'")
                    for item in items:
                        prod = {}
                        # Get text content
                        text = item.inner_text().strip()
                        # Try to parse name and price
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if lines:
                            prod["name"] = lines[0]
                            # Look for price pattern
                            for line in lines:
                                if "$" in line or "USD" in line:
                                    prod["price"] = line
                                    break

                        # Get link
                        link = item.query_selector("a[href*='/products/']")
                        if link:
                            prod["url"] = link.get_attribute("href")

                        if prod.get("name") and len(prod["name"]) > 2:
                            products.append(prod)
                    break

            if not products:
                # Fallback: get all product links
                product_links = page.query_selector_all("a[href*='/products/']")
                seen = set()
                for pl in product_links:
                    href = pl.get_attribute("href") or ""
                    text = pl.inner_text().strip()
                    if href not in seen and text and len(text) > 2:
                        seen.add(href)
                        products.append({"name": text, "url": href})

            # Also try extracting from Shopify JSON
            try:
                shopify_data = page.evaluate("""
                    () => {
                        // Shopify puts collection data in script tags
                        const scripts = document.querySelectorAll('script');
                        for (const s of scripts) {
                            const text = s.textContent;
                            if (text.includes('"products"') && text.includes('"variants"')) {
                                const match = text.match(/\\{[^]*"products"[^]*\\}/);
                                if (match) {
                                    try { return JSON.parse(match[0]); } catch(e) {}
                                }
                            }
                        }
                        // Try window.__NEXT_DATA__ or similar
                        if (window.__NEXT_DATA__) return window.__NEXT_DATA__;
                        return null;
                    }
                """)
                if shopify_data:
                    results[f"{name}_shopify_json"] = shopify_data
                    print(f"    Got Shopify JSON data!")
            except:
                pass

            results[name] = {
                "url": url,
                "products": products,
                "body_preview": page.inner_text("body")[:3000],
            }
            print(f"    Total products: {len(products)}")
            for p in products[:5]:
                print(f"      - {p.get('name', '?')[:50]} {p.get('price', '')}")

        except Exception as e:
            print(f"    Error: {e}")
            results[name] = {"error": str(e)}

    return results


def scrape_product_details_batch(page, product_urls):
    """Scrape details from individual product pages."""
    results = {}

    print(f"\n=== Scraping {len(product_urls)} product detail pages ===")

    for i, (name, url) in enumerate(product_urls[:50]):  # Max 50
        if not url.startswith("http"):
            url = f"https://www.mcelroyparts.com{url}"
        try:
            page.goto(url, timeout=15000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            time.sleep(1)

            detail = {}

            # Try Shopify product JSON (most reliable)
            try:
                prod_json = page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script[type="application/json"]');
                        for (const s of scripts) {
                            try {
                                const d = JSON.parse(s.textContent);
                                if (d.product) return d.product;
                            } catch(e) {}
                        }
                        // Also try the product JSON endpoint
                        return null;
                    }
                """)
                if prod_json:
                    detail["shopify"] = prod_json
            except:
                pass

            # Fallback to DOM scraping
            for sel, key in [
                ("h1", "title"),
                (".product-single__description, .product-description, .rte", "description"),
                (".product__price, .price--main .money, .product-single__price", "price"),
            ]:
                el = page.query_selector(sel)
                if el:
                    detail[key] = el.inner_text().strip()[:500]

            # Get body text for parsing
            detail["body_preview"] = page.inner_text("body")[:2000]

            results[url] = detail
            title = detail.get("title", name)[:40]
            print(f"  [{i+1}] {title}")

        except Exception as e:
            print(f"  [{i+1}] Error: {e}")

    return results


def main():
    all_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()

        # 1. Official parts finder
        try:
            all_data["official"] = scrape_official_parts_finder(page)
        except Exception as e:
            print(f"Official scrape failed: {e}")

        # 2. mcelroyparts.com with proper JS waiting
        try:
            store_data = scrape_mcelroyparts_collections_js(page)
            all_data["store"] = store_data

            # Collect product URLs for detail scraping
            product_urls = []
            for coll_name, coll_data in store_data.items():
                if isinstance(coll_data, dict) and "products" in coll_data:
                    for prod in coll_data["products"]:
                        if prod.get("url"):
                            product_urls.append((prod.get("name", ""), prod["url"]))

            # 3. Scrape product details
            if product_urls:
                all_data["details"] = scrape_product_details_batch(page, product_urls)
        except Exception as e:
            print(f"Store scrape failed: {e}")

        browser.close()

    # Save
    out_file = OUTPUT_DIR / "mcelroy_official.json"
    with open(out_file, "w") as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\nSaved to {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
