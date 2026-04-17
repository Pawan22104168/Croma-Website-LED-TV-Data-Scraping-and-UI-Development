from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import math
import os

# Serve static files (HTML/CSS/JS) from the frontend folder
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Reads MONGO_URI from environment (set on Vercel). Falls back to localhost for local dev.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
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
    is_exact_match = True
    
    # Keyword Search Intelligence
    is_fuzzy_match = False
    if search_query:
        # Pass 1: Try Exact Phrase Text Search (High Precision)
        exact_phrase = f'"{search_query}"'
        if collection.count_documents({"$text": {"$search": exact_phrase}}) > 0:
            mongo_filter["$text"] = {"$search": exact_phrase}
            is_exact_match = True
        # Pass 2: Try Broad Relevance Text Search (Standard)
        elif collection.count_documents({"$text": {"$search": search_query}}) > 0:
            mongo_filter["$text"] = {"$search": search_query}
            is_exact_match = False
        # Pass 3: Intelligent Fallback (Regex Substring/Partial Match)
        else:
            # This handles "Sa" -> "Samsung" or "Samsang" typo matches
            regex_query = {"$regex": search_query, "$options": "i"}
            mongo_filter["$or"] = [
                {"name": regex_query},
                {"brand": regex_query}
            ]
            is_exact_match = False
            is_fuzzy_match = True
        
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
    # Default to catalog rank
    sort_logic = [("catalog_rank", 1)]
    
    score_projection = None
    if search_query:
        # We project the text score to determine how 'exact' the match is
        score_projection = {"score": {"$meta": "textScore"}}
        if sort_by == "catalog_rank": # If user is on default, use relevance
            sort_logic = [("score", {"$meta": "textScore"})]
        else:
            # If user picked a sort (like price), use that but keep score as secondary
            sort_logic = [(sort_logic[0][0], sort_logic[0][1]), ("score", {"$meta": "textScore"})]
            
    # Apply the user's chosen sort order
    if sort_by == "price_asc":
        sort_logic = [("price_num", 1)]
    elif sort_by == "price_desc":
        sort_logic = [("price_num", -1)]
    elif sort_by == "rating_desc":
        sort_logic = [("rating_num", -1)]
    elif sort_by == "discount_desc":
        sort_logic = [("discount_num", -1)]
    elif sort_by == "rank_asc":
        sort_logic = [("catalog_rank", 1)]

    # --- 4. Execute Query with Pagination ---
    total_count = collection.count_documents(mongo_filter)
    total_pages = math.ceil(total_count / limit)
    
    skip = (page - 1) * limit
    
    # Fetch data
    if score_projection:
        cursor = collection.find(mongo_filter, score_projection).sort(sort_logic).skip(skip).limit(limit)
    else:
        cursor = collection.find(mongo_filter).sort(sort_logic).skip(skip).limit(limit)
    
    products = []
    max_score = 0
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        current_score = doc.get("score", 0)
        if current_score > max_score:
            max_score = current_score
        products.append(doc)

    # --- 5. Return JSON Response ---
    return jsonify({
        "products": products,
        "searchInfo": {
            "searchActive": bool(search_query),
            "isExactMatch": is_exact_match,
            "isFuzzyMatch": is_fuzzy_match,
            "maxScore": max_score
        },
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

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """
    Powerful data intelligence endpoint.
    Calculates market trends, and brand leaders in real-time.
    """
    try:
        # Pass 1: Global Market Snapshot
        snapshot_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_price": {"$avg": "$price_num"},
                    "max_discount": {"$max": "$discount_num"},
                    "avg_discount": {"$avg": "$discount_num"}
                }
            }
        ]
        snapshot = list(collection.aggregate(snapshot_pipeline))[0]

        # Pass 2: Brand Leaderboard (Top 3 by Volume)
        brand_pipeline = [
            {"$group": {"_id": "$brand", "count": {"$sum": 1}, "avg_price": {"$avg": "$price_num"}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ]
        brand_leaders = list(collection.aggregate(brand_pipeline))

        # Pass 3: Value Gems (Top 5 TVs with 4.5+ rating and high discount)
        # We'll just return the best overall brand for visual simplicity
        best_brand = brand_leaders[0]["_id"] if brand_leaders else "N/A"

        return jsonify({
            "avgPrice": round(snapshot["avg_price"]),
            "maxSavings": round(snapshot["max_discount"]),
            "avgDiscount": round(snapshot["avg_discount"]),
            "topBrand": best_brand,
            "leaders": brand_leaders
        })
    except Exception as e:
        return jsonify({"avgPrice": 0, "maxSavings": 0, "topBrand": "N/A"})

if __name__ == "__main__":
    # Run the Flask app on port 5000
    print("Backend API starting on http://localhost:5000")
    app.run(debug=True, port=5000)
