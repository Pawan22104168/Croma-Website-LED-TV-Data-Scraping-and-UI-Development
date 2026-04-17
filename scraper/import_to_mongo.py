import re # Used to extract numerical screen sizes from product names
from pymongo import MongoClient, TEXT

def extract_screen_size(name):
    """
    Normalization Logic: 
    Extracts numerical inch value from product strings (e.g., '32 inch').
    This enables precise filtering regardless of variations in the product title format.
    """
    match = re.search(r'(\d+)\s*(?:inch|inch)', name, re.IGNORECASE)
    return int(match.group(1)) if match else None

def import_products():
    # 1. Connect to local MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    
    # 2. Create/Access Database and Collection
    db = client["croma_db"]
    collection = db["products"]
    
    # 3. Load the scraped JSON data
    print("Reading data/products.json...")
    try:
        with open("data/products.json", "r", encoding="utf-8") as f:
            products = json.load(f)
    except FileNotFoundError:
        print("Error: data/products.json not found. Did you run the scraper?")
        return

    # 4. Clean and Prepare Data
    for prod in products:
        # Convert price value to float if it exists
        if "price" in prod and "value" in prod["price"]:
            prod["price_num"] = float(prod["price"]["value"])
        else:
            prod["price_num"] = 0.0
            
        # Convert averageRating to float
        prod["rating_num"] = float(prod.get("averageRating", 0.0))
        
        # Ensure brand exists (using manufacturer field)
        prod["brand"] = prod.get("manufacturer", "Unknown")

        # Extract screen size for advanced filtering and bucketing
        prod["screen_size_num"] = extract_screen_size(prod["name"])

        # Extract numerical discount percentage for the Deal Finder feature
        discount_str = prod.get("discountValue", "")
        if "%" in discount_str:
            # Extract only digits (e.g., "38%" -> 38)
            discount_match = re.search(r'(\d+)', discount_str)
            prod["discount_num"] = int(discount_match.group(1)) if discount_match else 0
        else:
            prod["discount_num"] = 0

    print("Clearing old data from collection...")
    collection.delete_many({})
    db["metadata"].delete_many({}) 

    print(f"Inserting {len(products)} products into MongoDB...")
    for index, prod in enumerate(products):
        prod["catalog_rank"] = index + 1 # Rank starts at 1
        collection.insert_one(prod)

    # Record the ingestion timestamp for data freshness transparency
    from datetime import datetime
    db["metadata"].insert_one({
        "last_updated": datetime.now().strftime("%B %d, %Y at %I:%M %p")
    })

    # 7. Create Indexes for Performance (Scaling)
    print("Creating database indexes...")
    
    # Text index for search bar (Search by name, brand, or description)
    collection.create_index([
        ("name", TEXT),
        ("brand", TEXT),
        ("quickViewDesc", TEXT)
    ], name="search_index")
    
    # Field indexes for fast sorting
    collection.create_index([("price_num", 1)], name="price_index")
    collection.create_index([("rating_num", -1)], name="rating_index")
    collection.create_index([("catalog_rank", 1)], name="rank_index")

    print("\nSUCCESS: Data imported and indexed in MongoDB.")
    print(f"Database: croma_db")
    print(f"Collection: products")

if __name__ == "__main__":
    import_products()
