import asyncio
import json
import time
from playwright.async_api import async_playwright

# --- Concurrency Configuration ---
# Controls how many API pages are fetched simultaneously.
# Increasing this value speeds up scraping but adds more load on the server.
MAX_CONCURRENT_REQUESTS = 5

# --- API & URL Constants ---
API_BASE = "https://api.croma.com/searchservices/v1/search"
SEARCH_PAGE = "https://www.croma.com/searchB?q=led%20tv%3Arelevance&text=led%20tv"
API_HEADERS = {
    'Referer': 'https://www.croma.com/',
    'Origin': 'https://www.croma.com'
}


def build_api_url(page_num):
    """Constructs the paginated Croma search API URL for a given page number."""
    return (
        f"{API_BASE}?currentPage={page_num}"
        f"&query=led%20tv%3Arelevance&fields=FULL"
        f"&channel=WEB&channelCode=400049&spellOpt=DEFAULT"
    )


async def fetch_page_data(context, page_num, semaphore):
    """
    Fetches product data for a single API page.

    Uses a Semaphore to enforce a limit on the number of pages being 
    fetched at the same time. This prevents overloading the server 
    while still running faster than sequential scraping.

    Returns a list of product dictionaries, or an empty list on failure.
    """
    async with semaphore:
        try:
            response = await context.request.get(
                build_api_url(page_num),
                headers=API_HEADERS
            )
            if response.status == 200:
                data = await response.json()
                products = data.get("products", [])
                print(f"  [OK] Page {page_num + 1}: Retrieved {len(products)} products.")
                return products
            else:
                print(f"  [FAIL] Page {page_num + 1}: HTTP {response.status}.")
                return []
        except Exception as e:
            print(f"  [ERROR] Page {page_num + 1}: {e}")
            return []


async def scrape_croma_tvs():
    """
    Main scraping orchestrator.

    Flow:
    1. Launch a headless browser and establish a session with croma.com.
       (Required to get authenticated cookies for API access.)
    2. Fetch page 0 sequentially to discover the total page count.
    3. Create async tasks for all remaining pages and run them
       concurrently using asyncio.gather() with a Semaphore.
    4. Preserve API ordering to ensure catalog_rank is accurate.
    5. Save the consolidated product list to data/products.json.
    """
    print("=" * 55)
    print("  Croma LED TV Scraper  |  Concurrent Mode")
    print(f"  Workers: {MAX_CONCURRENT_REQUESTS} simultaneous requests")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # Step 1: Establish an authenticated session
        print("\n[Step 1] Establishing browser session with croma.com...")
        await page.goto(SEARCH_PAGE, wait_until="networkidle")
        print("         Session established.")

        # Step 2: Fetch page 0 to get catalog metadata (total page count)
        print("\n[Step 2] Fetching catalog metadata from API...")
        first_response = await context.request.get(
            build_api_url(0), headers=API_HEADERS
        )
        if first_response.status != 200:
            print(f"         ERROR: Could not connect to Croma API (HTTP {first_response.status}). Exiting.")
            await browser.close()
            return

        first_data = await first_response.json()
        total_pages = first_data.get("pagination", {}).get("totalPages", 1)
        first_page_products = first_data.get("products", [])
        print(f"         Total pages in catalog: {total_pages}")
        print(f"         Estimated products: ~{total_pages * len(first_page_products)}")

        # Step 3: Scrape all remaining pages concurrently
        print(f"\n[Step 3] Launching {MAX_CONCURRENT_REQUESTS} concurrent workers for {total_pages - 1} pages...")
        start_time = time.time()

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = [
            fetch_page_data(context, page_num, semaphore)
            for page_num in range(1, total_pages)
        ]
        # asyncio.gather preserves task order, ensuring correct catalog ranking
        concurrent_results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Step 4: Consolidate results in the correct catalog order
        all_products = first_page_products
        for page_products in concurrent_results:
            all_products.extend(page_products)

        rate = len(all_products) / elapsed if elapsed > 0 else 0
        print(f"\n[Step 4] Consolidation complete.")
        print(f"         Total products: {len(all_products)}")
        print(f"         Time taken:     {elapsed:.1f} seconds")
        print(f"         Scrape rate:    {rate:.1f} products/second")

        # Step 5: Save raw data to JSON
        print("\n[Step 5] Saving to data/products.json...")
        with open("data/products.json", "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4)
        print(f"         Saved {len(all_products)} products successfully.")

        await browser.close()

    print("\n" + "=" * 55)
    print("  Scraping Complete!")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(scrape_croma_tvs())
