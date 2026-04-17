import asyncio
import json
from playwright.async_api import async_playwright

async def scrape_croma_tvs():
    async with async_playwright() as p:
        # 1. Launch a headless browser
        # We use a real browser to handle any underlying JS or security checks easily
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 2. Define the exact API URL and the Page URL
        api_url = "https://api.croma.com/searchservices/v1/search?currentPage=0&query=led%20tv%3Arelevance&fields=FULL&channel=WEB&channelCode=400049&spellOpt=DEFAULT"
        search_page = "https://www.croma.com/searchB?q=led%20tv%3Arelevance&text=led%20tv"

        print(f"Opening Croma search page to establish session...")
        await page.goto(search_page, wait_until="networkidle")

        all_products = []
        current_page = 0
        total_pages = 1 # We will update this from the first response

        while current_page < total_pages:
            print(f"Fetching Page {current_page} of {total_pages}...")
            
            # Update the API URL with the current page
            current_api_url = f"https://api.croma.com/searchservices/v1/search?currentPage={current_page}&query=led%20tv%3Arelevance&fields=FULL&channel=WEB&channelCode=400049&spellOpt=DEFAULT"
            
            api_response = await context.request.get(current_api_url, headers={
                'Referer': 'https://www.croma.com/',
                'Origin': 'https://www.croma.com'
            })

            if api_response.status == 200:
                response_json = await api_response.json()
                
                # Update total pages from the first response
                if current_page == 0:
                    total_pages = response_json.get("pagination", {}).get("totalPages", 1)
                    print(f"Total pages found: {total_pages}")

                page_products = response_json.get("products", [])
                all_products.extend(page_products)
                print(f"Added {len(page_products)} products. Total collected: {len(all_products)}")

                current_page += 1
                
                # Ethical Scraping: Add a small delay between requests
                if current_page < total_pages:
                    await asyncio.sleep(2) 
            else:
                print(f"Failed to fetch Page {current_page}. Status: {api_response.status}")
                break

        # 4. Save the results to a JSON file
        with open("data/products.json", "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4)
        print(f"\nSUCCESS: Scraped {len(all_products)} products total.")
        print(f"Saved to data/products.json")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_croma_tvs())
