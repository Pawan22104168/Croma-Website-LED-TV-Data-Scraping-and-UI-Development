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

    # --- 2. Build MongoDB Filter Object ---
    mongo_filter = {}
    
    # Keyword Search (uses the Text Index we created)
    if search_query:
        mongo_filter["$text"] = {"$search": search_query}
        
    # Brand Filter
    if brand_filter:
        mongo_filter["brand"] = brand_filter
        
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

@app.route("/api/stats", methods=["GET"])
def get_stats():
    # Returns some summary stats for the UI
    total = collection.count_documents({})
    # Get min and max price
    pipeline = [
        {"$group": {"_id": None, "min": {"$min": "$price_num"}, "max": {"$max": "$price_num"}}}
    ]
    result = list(collection.aggregate(pipeline))
    stats = {
        "totalProducts": total,
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
