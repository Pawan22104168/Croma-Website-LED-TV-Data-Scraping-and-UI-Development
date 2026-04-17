from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import math
app = Flask(__name__, 
            static_folder='../frontend', 
            static_url_path='')
# Enable CORS so our frontend can talk to this API
CORS(app)

# 2. Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["croma_db"]
collection = db["products"]

@app.route("/")
def serve_ui():
    # This serves the index.html file when you visit http://localhost:5000
    return app.send_static_file("index.html")

@app.route("/api/products", methods=["GET"])
def get_products():
    # --- 1. Get Query Parameters ---
    search_query = request.args.get("search", "")
    sort_by = request.args.get("sort", "catalog_rank") # Default sort
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    
    # Filter params
    brand_filter = request.args.get("brand", "")
    min_price = request.args.get("min_price", None)
    max_price = request.args.get("max_price", None)
    screen_size_filter = request.args.get("screen_size", "")
    discount_filter = request.args.get("discount", "")

    # --- 2. Build MongoDB Filter Object ---
    mongo_filter = {}
    
    # Keyword Search (uses the Text Index we created)
    if search_query:
        mongo_filter["$text"] = {"$search": search_query}
        
    # Brand Filter
    if brand_filter:
        mongo_filter["brand"] = brand_filter

    # Implement Discount Filter Logic
    if discount_filter:
        mongo_filter["discount_num"] = {"$gte": int(discount_filter)}

    # Screen Size logic supporting both legacy buckets and dynamic exact matches
    if screen_size_filter:
        if screen_size_filter == "32_and_below":
            mongo_filter["screen_size_num"] = {"$lte": 32}
        elif screen_size_filter == "43_inch":
            mongo_filter["screen_size_num"] = 43
        elif screen_size_filter == "50_inch":
            mongo_filter["screen_size_num"] = 50
        elif screen_size_filter == "55_inch":
            mongo_filter["screen_size_num"] = 55
        elif screen_size_filter == "65_and_above":
            mongo_filter["screen_size_num"] = {"$gte": 65}
        else:
            # Handle dynamic exact numerical matches from the configuration-driven UI
            try:
                mongo_filter["screen_size_num"] = int(screen_size_filter)
            except ValueError:
                pass 
        
    # Price Range Filter
    if min_price or max_price:
        mongo_filter["price_num"] = {}
        if min_price:
            mongo_filter["price_num"]["$gte"] = float(min_price)
        if max_price:
            mongo_filter["price_num"]["$lte"] = float(max_price)

    # --- 3. Determine Sort Logic ---
    # catalog_rank: 1 (default)
    # price_asc: 1
    # price_desc: -1
    # rating_desc: -1
    sort_logic = [("catalog_rank", 1)] # Default
    
    if sort_by == "price_asc":
        sort_logic = [("price_num", 1)]
    elif sort_by == "price_desc":
        sort_logic = [("price_num", -1)]
    elif sort_by == "rating_desc":
        sort_logic = [("rating_num", -1)]
    elif sort_by == "rank_asc":
        sort_logic = [("catalog_rank", 1)]

    # --- 4. Execute Query with Pagination ---
    total_count = collection.count_documents(mongo_filter)
    total_pages = math.ceil(total_count / limit)
    
    skip = (page - 1) * limit
    
    # Fetch data
    cursor = collection.find(mongo_filter).sort(sort_logic).skip(skip).limit(limit)
    
    products = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"]) # Convert ObjectId to string for JSON
        products.append(doc)

    # --- 5. Return JSON Response ---
    return jsonify({
        "products": products,
        "pagination": {
            "totalResults": total_count,
            "totalPages": total_pages,
            "currentPage": page,
            "pageSize": limit
        }
    })

@app.route("/api/brands", methods=["GET"])
def get_brands():
    # Returns a unique list of all brands in the database
    brands = collection.distinct("brand")
    return jsonify(sorted(brands))

@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Analyzes the database in real-time to generate dynamic filter categories.
    This ensures the UI scales automatically as the catalog grows.
    """
    try:
        # 1. Dynamically find every screen size in stock
        # Removing None values and sorting from small to large
        distinct_sizes = sorted([s for s in collection.distinct("screen_size_num") if s])
        
        screen_sizes = [{"label": "All Sizes", "value": ""}]
        for size in distinct_sizes:
            screen_sizes.append({
                "label": f"{size} inch",
                "value": str(size)
            })

        # 2. Dynamically determine discount thresholds
        # If the highest discount in DB is 54%, we show 10, 25, 40 etc.
        # If today only 5% exists, we can still show 5% as an option.
        pipeline = [{"$group": {"_id": None, "max_d": {"$max": "$discount_num"}}}]
        res = list(collection.aggregate(pipeline))
        max_d = res[0]["max_d"] if res else 0

        deals = [{"label": "All Products", "value": ""}]
        # Offer standard industry milestones if they are relevant to the current data
        for threshold in [5, 10, 25, 40, 50, 75]:
            if max_d >= threshold:
                deals.append({"label": f"{threshold}% Off or More", "value": str(threshold)})

        return jsonify({
            "screenSizes": screen_sizes,
            "deals": deals
        })
    except Exception as e:
        print(f"Config API Error: {e}")
        return jsonify({"screenSizes": [], "deals": []})

@app.route("/api/stats", methods=["GET"])
def get_stats():
    # Returns some summary stats for the UI
    total = collection.count_documents({})

    # Fetch the Metadata for data freshness tracking
    meta = db["metadata"].find_one()
    last_updated = meta.get("last_updated", "Unknown") if meta else "Recent"

    # Get min and max price
    pipeline = [
        {"$group": {"_id": None, "min": {"$min": "$price_num"}, "max": {"$max": "$price_num"}}}
    ]
    result = list(collection.aggregate(pipeline))
    stats = {
        "totalProducts": total,
        "lastUpdated": last_updated,
        "priceRange": {
            "min": result[0]["min"] if result else 0,
            "max": result[0]["max"] if result else 0
        }
    }
    return jsonify(stats)

if __name__ == "__main__":
    # Run the Flask app on port 5000
    print("Backend API starting on http://localhost:5000")
    app.run(debug=True, port=5000)
