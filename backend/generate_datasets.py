"""
=============================================================================
 DATASET GENERATOR — Product Recommendation System
 Hackathon: CloudFront Data & AI Campus Drive
=============================================================================
 Generates three production-grade CSV datasets:
   1. users.csv        — 500 users with demographics
   2. products.csv     — 200 products across categories
   3. interactions.csv — ~15,000 user-product interactions
 Also exports pre-computed JSON files for the frontend demo.
=============================================================================
"""

import csv
import json
import random
import os
import hashlib
from datetime import datetime, timedelta

random.seed(42)

# ── Output directories ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DATA_DIR = os.path.join(BASE_DIR, "..", "frontend", "data")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FRONTEND_DATA_DIR, exist_ok=True)

# ── Constants ────────────────────────────────────────────────────────────────
NUM_USERS = 500
NUM_PRODUCTS = 200
NUM_INTERACTIONS = 15000

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
LOCATIONS = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Chandigarh", "Indore", "Bhopal", "Kochi", "Coimbatore"
]
MEMBERSHIP_TYPES = ["Free", "Silver", "Gold", "Platinum"]

CATEGORIES = {
    "Electronics": {
        "sub_categories": ["Smartphones", "Laptops", "Headphones", "Tablets", "Smartwatches"],
        "brands": ["Samsung", "Apple", "Sony", "OnePlus", "Boat", "Lenovo", "HP", "Dell"],
        "price_range": (999, 149999),
    },
    "Fashion": {
        "sub_categories": ["T-Shirts", "Jeans", "Sneakers", "Jackets", "Dresses"],
        "brands": ["Nike", "Adidas", "Zara", "H&M", "Levis", "Puma", "US Polo"],
        "price_range": (299, 9999),
    },
    "Books": {
        "sub_categories": ["Fiction", "Non-Fiction", "Sci-Fi", "Self-Help", "Comics"],
        "brands": ["Penguin", "HarperCollins", "Scholastic", "Oxford", "Pearson"],
        "price_range": (99, 1999),
    },
    "Home & Kitchen": {
        "sub_categories": ["Cookware", "Furniture", "Decor", "Appliances", "Storage"],
        "brands": ["IKEA", "Prestige", "Philips", "Godrej", "Nilkamal", "Bajaj"],
        "price_range": (199, 49999),
    },
    "Sports": {
        "sub_categories": ["Cricket", "Football", "Fitness", "Yoga", "Running"],
        "brands": ["Nike", "Adidas", "Puma", "Yonex", "Decathlon", "Cosco"],
        "price_range": (199, 14999),
    },
    "Beauty": {
        "sub_categories": ["Skincare", "Haircare", "Makeup", "Fragrance", "Grooming"],
        "brands": ["Lakme", "Nivea", "Dove", "Maybelline", "LOreal", "Garnier"],
        "price_range": (99, 4999),
    },
}

INTERACTION_TYPES = ["view", "click", "add_to_cart", "purchase"]
INTERACTION_WEIGHTS = {"view": 1, "click": 2, "add_to_cart": 3, "purchase": 5}
SENTIMENTS = ["positive", "neutral", "negative"]

PRODUCT_NAME_PREFIXES = {
    "Electronics": ["Pro", "Ultra", "Max", "Lite", "Neo", "Air", "Edge"],
    "Fashion": ["Classic", "Urban", "Street", "Vintage", "Modern", "Elite"],
    "Books": ["The Art of", "Mastering", "Essential", "Complete Guide to", "Introduction to"],
    "Home & Kitchen": ["Premium", "Compact", "Elegant", "Smart", "Durable"],
    "Sports": ["Pro", "Elite", "Champion", "Turbo", "Victory"],
    "Beauty": ["Radiance", "Glow", "Pure", "Natural", "Luxe"],
}

# Cross-category complementary/accessory mappings
COMPLEMENTARY_SUBCATEGORIES = {
    "Smartphones": ["Headphones", "Smartwatches", "Tablets"],
    "Laptops":     ["Headphones", "Tablets", "Smartwatches"],
    "Headphones":  ["Smartphones", "Laptops", "Smartwatches"],
    "Tablets":     ["Smartphones", "Laptops", "Headphones"],
    "Smartwatches":["Smartphones", "Fitness", "Running"],
    "T-Shirts":    ["Jeans", "Sneakers", "Jackets"],
    "Jeans":       ["T-Shirts", "Sneakers", "Jackets"],
    "Sneakers":    ["T-Shirts", "Jeans", "Running"],
    "Jackets":     ["T-Shirts", "Jeans", "Sneakers", "Dresses"],
    "Dresses":     ["Sneakers", "Jackets", "Makeup"],
    "Fiction":     ["Non-Fiction", "Sci-Fi", "Comics"],
    "Non-Fiction": ["Self-Help", "Fiction"],
    "Sci-Fi":      ["Fiction", "Comics"],
    "Self-Help":   ["Non-Fiction", "Fitness", "Yoga"],
    "Comics":      ["Fiction", "Sci-Fi"],
    "Cookware":    ["Appliances", "Storage"],
    "Furniture":   ["Decor", "Storage"],
    "Decor":       ["Furniture", "Storage"],
    "Appliances":  ["Cookware", "Storage"],
    "Storage":     ["Cookware", "Furniture"],
    "Cricket":     ["Fitness", "Running"],
    "Football":    ["Fitness", "Running"],
    "Fitness":     ["Yoga", "Running", "Smartwatches"],
    "Yoga":        ["Fitness", "Self-Help"],
    "Running":     ["Sneakers", "Fitness", "Smartwatches"],
    "Skincare":    ["Haircare", "Makeup"],
    "Haircare":    ["Skincare", "Grooming"],
    "Makeup":      ["Skincare", "Fragrance", "Dresses"],
    "Fragrance":   ["Makeup", "Grooming"],
    "Grooming":    ["Skincare", "Haircare"],
}


# ═══════════════════════════════════════════════════════════════════════════
#  1. GENERATE USERS
# ═══════════════════════════════════════════════════════════════════════════
def generate_users():
    """Create 500 realistic user profiles."""
    users = []
    categories_list = list(CATEGORIES.keys())
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2025, 12, 31)

    for uid in range(1, NUM_USERS + 1):
        signup = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
        users.append({
            "user_id": uid,
            "age_group": random.choice(AGE_GROUPS),
            "location": random.choice(LOCATIONS),
            "preferred_category": random.choice(categories_list),
            "membership_type": random.choices(
                MEMBERSHIP_TYPES, weights=[40, 30, 20, 10], k=1
            )[0],
            "signup_date": signup.strftime("%Y-%m-%d"),
        })
    return users


# ═══════════════════════════════════════════════════════════════════════════
#  2. GENERATE PRODUCTS
# ═══════════════════════════════════════════════════════════════════════════
def generate_products():
    """Create 200 products distributed across categories."""
    products = []
    pid = 1
    products_per_category = NUM_PRODUCTS // len(CATEGORIES)

    for category, meta in CATEGORIES.items():
        for _ in range(products_per_category):
            sub_cat = random.choice(meta["sub_categories"])
            brand = random.choice(meta["brands"])
            prefix = random.choice(PRODUCT_NAME_PREFIXES[category])
            price = round(random.uniform(*meta["price_range"]), 2)
            avg_rating = round(random.uniform(2.5, 5.0), 1)

            # Determine price range bucket
            if price < 500:
                price_range = "Budget"
            elif price < 2000:
                price_range = "Mid-Range"
            elif price < 10000:
                price_range = "Premium"
            else:
                price_range = "Luxury"

            product_name = f"{brand} {prefix} {sub_cat[:-1] if sub_cat.endswith('s') else sub_cat}"

            products.append({
                "product_id": pid,
                "product_name": product_name,
                "category": category,
                "sub_category": sub_cat,
                "brand": brand,
                "price": price,
                "price_range": price_range,
                "avg_rating": avg_rating,
                "rating_count": random.randint(10, 5000),
                "stock": random.randint(0, 500),
            })
            pid += 1

    # Fill remaining products randomly
    categories_list = list(CATEGORIES.keys())
    while pid <= NUM_PRODUCTS:
        category = random.choice(categories_list)
        meta = CATEGORIES[category]
        sub_cat = random.choice(meta["sub_categories"])
        brand = random.choice(meta["brands"])
        prefix = random.choice(PRODUCT_NAME_PREFIXES[category])
        price = round(random.uniform(*meta["price_range"]), 2)
        avg_rating = round(random.uniform(2.5, 5.0), 1)
        if price < 500:
            price_range = "Budget"
        elif price < 2000:
            price_range = "Mid-Range"
        elif price < 10000:
            price_range = "Premium"
        else:
            price_range = "Luxury"

        product_name = f"{brand} {prefix} {sub_cat[:-1] if sub_cat.endswith('s') else sub_cat}"
        products.append({
            "product_id": pid,
            "product_name": product_name,
            "category": category,
            "sub_category": sub_cat,
            "brand": brand,
            "price": price,
            "price_range": price_range,
            "avg_rating": avg_rating,
            "rating_count": random.randint(10, 5000),
            "stock": random.randint(0, 500),
        })
        pid += 1

    return products


# ═══════════════════════════════════════════════════════════════════════════
#  3. GENERATE INTERACTIONS
# ═══════════════════════════════════════════════════════════════════════════
def generate_interactions(users, products):
    """Create ~15,000 user-product interactions with realistic patterns."""
    interactions = []
    product_ids = [p["product_id"] for p in products]
    product_by_category = {}
    for p in products:
        product_by_category.setdefault(p["category"], []).append(p["product_id"])

    start_ts = datetime(2024, 1, 1)
    end_ts = datetime(2025, 12, 31)

    for _ in range(NUM_INTERACTIONS):
        user = random.choice(users)
        uid = user["user_id"]

        # 60% chance user interacts with their preferred category
        if random.random() < 0.6 and user["preferred_category"] in product_by_category:
            pid = random.choice(product_by_category[user["preferred_category"]])
        else:
            pid = random.choice(product_ids)

        # Interaction funnel: views are most common, purchases are rare
        itype = random.choices(
            INTERACTION_TYPES, weights=[50, 30, 12, 8], k=1
        )[0]
        score = INTERACTION_WEIGHTS[itype]

        # Rating only for purchases and some add_to_carts
        rating = None
        sentiment = None
        if itype == "purchase":
            rating = random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 35, 37], k=1)[0]
            sentiment = "positive" if rating >= 4 else ("neutral" if rating == 3 else "negative")
        elif itype == "add_to_cart" and random.random() < 0.3:
            rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30], k=1)[0]
            sentiment = "positive" if rating >= 4 else ("neutral" if rating == 3 else "negative")

        ts = start_ts + timedelta(
            seconds=random.randint(0, int((end_ts - start_ts).total_seconds()))
        )
        # Session ID: hash of user + date to simulate sessions
        session_seed = f"{uid}-{ts.strftime('%Y-%m-%d-%H')}"
        session_id = hashlib.md5(session_seed.encode()).hexdigest()[:12]

        interactions.append({
            "user_id": uid,
            "product_id": pid,
            "interaction_type": itype,
            "interaction_score": score,
            "rating": rating if rating else "",
            "review_sentiment": sentiment if sentiment else "",
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": session_id,
        })

    return interactions


# ═══════════════════════════════════════════════════════════════════════════
#  4. WRITE CSV FILES
# ═══════════════════════════════════════════════════════════════════════════
def write_csv(filepath, data, fieldnames):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"  ✓ {filepath}  ({len(data)} rows)")


# ═══════════════════════════════════════════════════════════════════════════
#  5. GENERATE FRONTEND JSON DATA (simulates Databricks output)
# ═══════════════════════════════════════════════════════════════════════════
def build_product_lookup(products):
    return {p["product_id"]: p for p in products}


def generate_recommendations_json(users, products, interactions):
    """
    Simulate ALS-style recommendations for the frontend demo.
    In production, this JSON is exported from the Databricks notebook.
    """
    product_map = build_product_lookup(products)

    # ── Per-user recommendations ────────────────────────────────────────
    # Score = sum of interaction_scores per (user, product), pick top 5
    user_product_scores = {}
    for ix in interactions:
        key = (ix["user_id"], ix["product_id"])
        user_product_scores[key] = user_product_scores.get(key, 0) + ix["interaction_score"]

    user_recs = {}
    # Group by user
    user_scores = {}
    for (uid, pid), score in user_product_scores.items():
        user_scores.setdefault(uid, []).append((pid, score))

    for uid, scored in user_scores.items():
        scored.sort(key=lambda x: -x[1])
        # Recommend products NOT heavily interacted with (simulate collaborative filtering)
        top_pids = [pid for pid, _ in scored[:15]]
        all_pids = [p["product_id"] for p in products]
        unseen = [pid for pid in all_pids if pid not in top_pids]
        random.shuffle(unseen)
        # Mix: 2 from top interacted category + 3 collaborative
        recs = []
        user_cats = {}
        for pid in top_pids:
            if pid in product_map:
                cat = product_map[pid]["category"]
                user_cats[cat] = user_cats.get(cat, 0) + 1
        top_cat = max(user_cats, key=user_cats.get) if user_cats else random.choice(list(CATEGORIES.keys()))

        cat_products = [p for p in products if p["category"] == top_cat and p["product_id"] not in top_pids]
        cat_products.sort(key=lambda x: -x["avg_rating"])
        recs.extend([p["product_id"] for p in cat_products[:2]])
        recs.extend(unseen[:3])

        # Ensure exactly 5
        while len(recs) < 5:
            candidate = random.choice(all_pids)
            if candidate not in recs:
                recs.append(candidate)
        recs = recs[:5]

        user_recs[str(uid)] = [
            {
                "product_id": pid,
                "product_name": product_map[pid]["product_name"],
                "category": product_map[pid]["category"],
                "sub_category": product_map[pid]["sub_category"],
                "brand": product_map[pid]["brand"],
                "price": product_map[pid]["price"],
                "avg_rating": product_map[pid]["avg_rating"],
                "rating_count": product_map[pid]["rating_count"],
                "price_range": product_map[pid]["price_range"],
            }
            for pid in recs if pid in product_map
        ]

    # ── Popular products by category ────────────────────────────────────
    category_popular = {}
    cat_interaction_count = {}
    for ix in interactions:
        pid = ix["product_id"]
        if pid in product_map:
            cat = product_map[pid]["category"]
            cat_interaction_count.setdefault(cat, {})
            cat_interaction_count[cat][pid] = cat_interaction_count[cat].get(pid, 0) + ix["interaction_score"]

    for cat, pid_scores in cat_interaction_count.items():
        sorted_items = sorted(pid_scores.items(), key=lambda x: -x[1])[:8]
        category_popular[cat] = [
            {
                "product_id": pid,
                "product_name": product_map[pid]["product_name"],
                "category": cat,
                "brand": product_map[pid]["brand"],
                "price": product_map[pid]["price"],
                "avg_rating": product_map[pid]["avg_rating"],
                "rating_count": product_map[pid]["rating_count"],
                "popularity_score": score,
            }
            for pid, score in sorted_items if pid in product_map
        ]

    # ── Similar products (item-based: same category + sub_category) ─────
    similar_products = {}
    for p in products:
        same_sub = [
            {
                "product_id": q["product_id"],
                "product_name": q["product_name"],
                "category": q["category"],
                "sub_category": q["sub_category"],
                "brand": q["brand"],
                "price": q["price"],
                "avg_rating": q["avg_rating"],
                "similarity_score": round(random.uniform(0.7, 0.99), 2),
            }
            for q in products
            if q["product_id"] != p["product_id"]
            and q["sub_category"] == p["sub_category"]
        ]
        same_sub.sort(key=lambda x: -x["similarity_score"])
        similar_products[str(p["product_id"])] = same_sub[:5]

    # ── Complementary / accessory products (cross-category) ─────────────
    complementary_products = {}
    for p in products:
        comp_subcats = COMPLEMENTARY_SUBCATEGORIES.get(p["sub_category"], [])
        comp_items = [
            {
                "product_id": q["product_id"],
                "product_name": q["product_name"],
                "category": q["category"],
                "sub_category": q["sub_category"],
                "brand": q["brand"],
                "price": q["price"],
                "avg_rating": q["avg_rating"],
            }
            for q in products
            if q["product_id"] != p["product_id"]
            and q["sub_category"] in comp_subcats
        ]
        comp_items.sort(key=lambda x: -x["avg_rating"])
        complementary_products[str(p["product_id"])] = comp_items[:5]

    # ── Top rated products ──────────────────────────────────────────────
    top_rated = sorted(products, key=lambda x: (-x["avg_rating"], -x["rating_count"]))[:20]
    top_rated_list = [
        {
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "category": p["category"],
            "brand": p["brand"],
            "price": p["price"],
            "avg_rating": p["avg_rating"],
            "rating_count": p["rating_count"],
        }
        for p in top_rated
    ]

    # ── Products lookup ─────────────────────────────────────────────────
    products_json = [
        {
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "category": p["category"],
            "sub_category": p["sub_category"],
            "brand": p["brand"],
            "price": p["price"],
            "price_range": p["price_range"],
            "avg_rating": p["avg_rating"],
            "rating_count": p["rating_count"],
        }
        for p in products
    ]

    return user_recs, category_popular, similar_products, complementary_products, top_rated_list, products_json


def write_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ {filepath}")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print(" Product Recommendation System — Dataset Generator")
    print("=" * 60)

    print("\n[1/3] Generating users...")
    users = generate_users()

    print("[2/3] Generating products...")
    products = generate_products()

    print("[3/3] Generating interactions...")
    interactions = generate_interactions(users, products)

    print("\n── Writing CSV datasets ──")
    write_csv(
        os.path.join(DATA_DIR, "users.csv"), users,
        ["user_id", "age_group", "location", "preferred_category", "membership_type", "signup_date"],
    )
    write_csv(
        os.path.join(DATA_DIR, "products.csv"), products,
        ["product_id", "product_name", "category", "sub_category", "brand",
         "price", "price_range", "avg_rating", "rating_count", "stock"],
    )
    write_csv(
        os.path.join(DATA_DIR, "interactions.csv"), interactions,
        ["user_id", "product_id", "interaction_type", "interaction_score",
         "rating", "review_sentiment", "timestamp", "session_id"],
    )

    print("\n── Generating frontend JSON files ──")
    recs, popular, similar, complementary, top_rated, products_json = generate_recommendations_json(
        users, products, interactions
    )
    write_json(os.path.join(FRONTEND_DATA_DIR, "recommendations.json"), recs)
    write_json(os.path.join(FRONTEND_DATA_DIR, "popular_by_category.json"), popular)
    write_json(os.path.join(FRONTEND_DATA_DIR, "similar_products.json"), similar)
    write_json(os.path.join(FRONTEND_DATA_DIR, "complementary_products.json"), complementary)
    write_json(os.path.join(FRONTEND_DATA_DIR, "top_rated.json"), top_rated)
    write_json(os.path.join(FRONTEND_DATA_DIR, "products.json"), products_json)

    print("\n✅ All datasets generated successfully!")
    print(f"   CSV files  → {DATA_DIR}")
    print(f"   JSON files → {FRONTEND_DATA_DIR}")
    print("=" * 60)
