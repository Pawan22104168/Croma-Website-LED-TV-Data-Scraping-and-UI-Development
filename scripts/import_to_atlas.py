import json
import os
import re
from datetime import datetime
from pymongo import MongoClient

# --- CONFIGURATION ---
ATLAS_URI = "mongodb+srv://pawanwalke6_db_user:nzJ15wIc0sYfliJn@croma-cluster.qw3iudf.mongodb.net/?appName=croma-cluster"
DB_NAME = "croma_db"
COLLECTION_NAME = "products"
DATA_FILE = os.path.join("data", "products.json")

def extract_screen_size(name):
    match = re.search(r'(\d+)\s*inch', name, re.IGNORECASE)
    return int(match.group(1)) if match else None

def prepare_product(prod, rank):
    """
    Data Enrichment: Calculates the numeric fields needed for the UI.
    Without this, the Bento Grid shows NaN and brands show UNDEFINED.
    """
    # Price
    if "price" in prod and "value" in prod.get("price", {}):
        prod["price_num"] = float(prod["price"]["value"])
    else:
        prod["price_num"] = 0.0

    # Brand
    prod["brand"] = prod.get("manufacturer", "Croma")
    
    # Screen Size
    prod["screen_size_num"] = extract_screen_size(prod.get("name", ""))

    # Discount
    discount_str = prod.get("discountValue", "")
    if "%" in discount_str:
        discount_match = re.search(r'(\d+)', discount_str)
        prod["discount_num"] = int(discount_match.group(1)) if discount_match else 0
    else:
        prod["discount_num"] = 0

    prod["catalog_rank"] = rank
    return prod

def migrate():
    print("[MIGRATION] Starting ENRICHED migration to MongoDB Atlas...")

    # 1. Load local data
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            products = json.load(f)
        print(f"[DATA] Loaded {len(products)} products.")
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    # 2. Enrich data
    print("[ENRICH] Enriching data for UI compatibility...")
    enriched_products = [prepare_product(p, i+1) for i, p in enumerate(products)]

    # 3. Connect and Upload
    try:
        client = MongoClient(ATLAS_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        print("[CLEAN] Cleaning old data...")
        collection.delete_many({})
        
        print("[UPLOAD] Uploading clean data...")
        collection.insert_many(enriched_products)

        # 4. Save Metadata (Last Updated)
        db["metadata"].delete_many({})
        db["metadata"].insert_one({
            "last_updated": datetime.now().strftime("%B %d, %Y at %I:%M %p")
        })

        print("[SUCCESS] Refresh your Vercel site now.")
    except Exception as e:
        print(f"[CONNECTION ERROR] {e}")

if __name__ == "__main__":
    migrate()
