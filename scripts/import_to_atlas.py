import json
import os
from pymongo import MongoClient

# --- CONFIGURATION ---
ATLAS_URI = "mongodb+srv://pawanwalke6_db_user:nzJ15wIc0sYfliJn@croma-cluster.qw3iudf.mongodb.net/?appName=croma-cluster"
DB_NAME = "croma_db"
COLLECTION_NAME = "products"
DATA_FILE = os.path.join("data", "products.json")

def migrate():
    if "<db_password>" in ATLAS_URI:
        print("❌ ERROR: You need to replace <db_password> in the script with your actual password!")
        return

    print("🚀 Starting migration to MongoDB Atlas...")

    # 1. Load local data
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            products = json.load(f)
        print(f"📦 Loaded {len(products)} products from local file.")
    except Exception as e:
        print(f"❌ ERROR: Could not read {DATA_FILE}: {e}")
        return

    # 2. Connect to Atlas
    try:
        client = MongoClient(ATLAS_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
    except Exception as e:
        print(f"❌ ERROR: Could not connect to Atlas: {e}")
        return

    # 3. Clear existing and Upload
    print("🧹 Cleaning Atlas collection...")
    collection.delete_many({})
    
    print("📤 Uploading data...")
    if products:
        collection.insert_many(products)
        print(f"🎉 SUCCESS! {len(products)} products are now live on MongoDB Atlas.")
    else:
        print("⚠️ No products found to upload.")

if __name__ == "__main__":
    migrate()
