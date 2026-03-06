"""
SmartRec AI — REST API Server
Serves the recommendation JSON data produced by the Databricks pipeline.
The frontend calls these endpoints instead of reading static JSON files.

Usage:
    pip install flask flask-cors
    python backend/api_server.py

Endpoints:
    GET /api/products                → Full product catalog
    GET /api/recommendations         → All user recommendations
    GET /api/recommendations/<uid>   → Recommendations for one user
    GET /api/popular                 → Popular products by category
    GET /api/similar/<pid>           → Similar products for a product
    GET /api/complementary/<pid>     → Complementary/accessory products
    GET /api/toprated                → Top rated products
    GET /api/health                  → Health check
"""

import json
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, abort
from flask_cors import CORS

# ── Resolve data directory ──────────────────────────────────────────────────
# The JSON files live in frontend/data/ (generated locally or downloaded from Databricks)
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "frontend" / "data"

app = Flask(__name__)
CORS(app)  # Allow frontend on any port to call this API

# ── Load JSON files into memory on startup ──────────────────────────────────
_cache = {}

def _load(filename):
    """Load a JSON file from DATA_DIR, cache it in memory."""
    if filename not in _cache:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"⚠️  Missing: {filepath}")
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]

def _reload_all():
    """Force-reload all data files (call after downloading new data from Databricks)."""
    _cache.clear()
    files = [
        "products.json", "recommendations.json", "popular_by_category.json",
        "similar_products.json", "complementary_products.json", "top_rated.json",
    ]
    for f in files:
        _load(f)
    print(f"✅ Loaded {len(_cache)} data files from {DATA_DIR}")

# ── API Endpoints ───────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "data_dir": str(DATA_DIR), "files_loaded": list(_cache.keys())})

@app.route("/api/products")
def get_products():
    data = _load("products.json")
    if data is None:
        abort(503, description="products.json not found")
    return jsonify(data)

@app.route("/api/recommendations")
def get_all_recommendations():
    data = _load("recommendations.json")
    if data is None:
        abort(503, description="recommendations.json not found")
    return jsonify(data)

@app.route("/api/recommendations/<uid>")
def get_user_recommendations(uid):
    data = _load("recommendations.json")
    if data is None:
        abort(503, description="recommendations.json not found")
    user_recs = data.get(str(uid), [])
    return jsonify(user_recs)

@app.route("/api/popular")
def get_popular():
    data = _load("popular_by_category.json")
    if data is None:
        abort(503, description="popular_by_category.json not found")
    return jsonify(data)

@app.route("/api/similar/all")
def get_all_similar():
    data = _load("similar_products.json")
    if data is None:
        abort(503, description="similar_products.json not found")
    return jsonify(data)

@app.route("/api/similar/<pid>")
def get_similar(pid):
    data = _load("similar_products.json")
    if data is None:
        abort(503, description="similar_products.json not found")
    similar = data.get(str(pid), [])
    return jsonify(similar)

@app.route("/api/complementary/all")
def get_all_complementary():
    data = _load("complementary_products.json")
    if data is None:
        abort(503, description="complementary_products.json not found")
    return jsonify(data)

@app.route("/api/complementary/<pid>")
def get_complementary(pid):
    data = _load("complementary_products.json")
    if data is None:
        abort(503, description="complementary_products.json not found")
    comp = data.get(str(pid), [])
    return jsonify(comp)

@app.route("/api/toprated")
def get_top_rated():
    data = _load("top_rated.json")
    if data is None:
        abort(503, description="top_rated.json not found")
    return jsonify(data)

@app.route("/api/reload", methods=["POST"])
def reload_data():
    """Reload all JSON files from disk (use after downloading fresh data from Databricks)."""
    _reload_all()
    return jsonify({"status": "reloaded", "files": list(_cache.keys())})

# ── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DATA_DIR.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        print("   Run 'python backend/generate_datasets.py' first.")
        sys.exit(1)

    _reload_all()

    print("=" * 55)
    print("   🚀 SmartRec AI — API Server")
    print(f"   http://localhost:5000/api/health")
    print("=" * 55)

    app.run(host="0.0.0.0", port=5000, debug=False)
