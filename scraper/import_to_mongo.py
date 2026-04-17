import json
import re
import time
from datetime import datetime
import os
from pymongo import MongoClient, UpdateOne, TEXT


def extract_screen_size(name):
    """
    Normalization Logic:
    Extracts a numerical inch value from a product title string.
    Example: 'Croma 139 cm (55 inch) 4K TV' -> 55

    Uses regex to find the first number followed by the word 'inch'.
    Returns None if no match is found, which is handled gracefully by
    the filtering logic.
    """
    match = re.search(r'(\d+)\s*inch', name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def prepare_product(prod, rank):
    """
    Data Enrichment Pipeline:
    Takes a raw product dictionary from Croma's API and enriches it
    with computed, numerical fields required for high-performance
    database filtering and sorting.

    Fields added:
    - price_num    : float version of price for range queries
    - rating_num   : float version of rating for sort queries
    - brand        : normalized brand name from manufacturer field
    - screen_size_num : integer inch value for exact-match filtering
    - discount_num : integer discount % for threshold-based filtering
    - catalog_rank : position in Croma's official catalog ordering
    """
    # Price normalization
    if "price" in prod and "value" in prod.get("price", {}):
        prod["price_num"] = float(prod["price"]["value"])
    else:
        prod["price_num"] = 0.0

    # Rating normalization
    prod["rating_num"] = float(prod.get("averageRating", 0.0))

    # Brand normalization
    prod["brand"] = prod.get("manufacturer", "Unknown")

    # Screen size extraction
    prod["screen_size_num"] = extract_screen_size(prod.get("name", ""))

    # Discount percentage extraction
    discount_str = prod.get("discountValue", "")
    if "%" in discount_str:
        discount_match = re.search(r'(\d+)', discount_str)
        prod["discount_num"] = int(discount_match.group(1)) if discount_match else 0
    else:
        prod["discount_num"] = 0

    # Catalog rank (position from the API's natural ordering)
    prod["catalog_rank"] = rank

    return prod


def import_products():
    """
    Database Import Orchestrator using Upsert Strategy.

    Why Upsert instead of Delete + Insert?
    - DELETE + INSERT: Wipes the entire database on every run. Any price 
      history or custom data is permanently lost. Also, if the scraper 
      fails midway, the database is left empty.
    - UPSERT (Update + Insert): For each product, MongoDB looks up its 
      unique URL. If found, it UPDATES the price, discount, and rating. 
      If not found, it INSERTS it as a new product. The database is 
      never left in a broken state.

    This approach handles three critical business cases:
    1. New product added by Croma -> INSERTED automatically.
    2. Existing product with a price change -> UPDATED automatically.
    3. Existing product with no changes -> MATCHED but not modified (efficient).
    """
    print("=" * 55)
    print("  Croma DB Importer  |  Upsert Mode")
    print("=" * 55)

    # Connect to MongoDB — uses Atlas Cloud URI for true dynamics
    atlas_uri = "mongodb+srv://pawanwalke6_db_user:nzJ15wIc0sYfliJn@croma-cluster.qw3iudf.mongodb.net/?appName=croma-cluster"
    client = MongoClient(atlas_uri)
    db = client["croma_db"]
    collection = db["products"]

    # Step 1: Load raw scraped data
    print("\n[Step 1] Loading data/products.json...")
    try:
        with open("data/products.json", "r", encoding="utf-8") as f:
            products = json.load(f)
        print(f"         Loaded {len(products)} products from file.")
    except FileNotFoundError:
        print("         ERROR: data/products.json not found. Run the scraper first.")
        return

    # Step 2: Enrich all products with computed fields
    print("\n[Step 2] Running data enrichment pipeline...")
    prepared_products = [
        prepare_product(prod, rank + 1)
        for rank, prod in enumerate(products)
    ]
    print(f"         Enrichment complete for {len(prepared_products)} products.")

    # Step 3: Build and execute bulk upsert operations
    print("\n[Step 3] Building bulk upsert operations...")
    print("         Strategy: Match on product URL (unique key).")
    print("         -> New products will be INSERTED.")
    print("         -> Existing products will have prices UPDATED.")

    operations = []
    for prod in prepared_products:
        prod.pop("_id", None)  # Remove any existing MongoDB ID to prevent conflicts
        operations.append(
            UpdateOne(
                {"url": prod["url"]},   # Unique match condition
                {"$set": prod},          # Update all fields with latest data
                upsert=True              # Insert the document if no match is found
            )
        )

    start_time = time.time()
    # ordered=False allows MongoDB to process all operations without stopping on error
    result = collection.bulk_write(operations, ordered=False)
    elapsed = time.time() - start_time

    print(f"\n         Upsert Results ({elapsed:.2f}s):")
    print(f"         + Inserted (new products):         {result.upserted_count}")
    print(f"         ~ Updated (price/data changes):    {result.modified_count}")
    print(f"         = Unchanged (no new data):         {result.matched_count - result.modified_count}")

    # Step 4: Update the metadata timestamp
    db["metadata"].delete_many({})
    db["metadata"].insert_one({
        "last_updated": datetime.now().strftime("%B %d, %Y at %I:%M %p")
    })

    # Step 5: Create indexes if they don't already exist
    print("\n[Step 4] Verifying database indexes...")
    existing_indexes = {idx["name"] for idx in collection.list_indexes()}

    if "search_index" not in existing_indexes:
        collection.create_index(
            [("name", TEXT), ("brand", TEXT), ("quickViewDesc", TEXT)],
            name="search_index"
        )
        print("         [Created] Full-text search index.")
    else:
        print("         [Exists]  Full-text search index.")

    for index_name, field, direction in [
        ("price_index",  "price_num",    1),
        ("rating_index", "rating_num",  -1),
        ("rank_index",   "catalog_rank", 1),
    ]:
        if index_name not in existing_indexes:
            collection.create_index([(field, direction)], name=index_name)
            print(f"         [Created] {index_name}.")
        else:
            print(f"         [Exists]  {index_name}.")

    print("\n" + "=" * 55)
    print(f"  Import Complete! DB: croma_db | Collection: products")
    print("=" * 55)


if __name__ == "__main__":
    import_products()
