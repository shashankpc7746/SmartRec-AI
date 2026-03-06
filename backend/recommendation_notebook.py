# Databricks notebook source

# MAGIC %md
# MAGIC # 🛒 AI Product Recommendation System
# MAGIC ### CloudFront Data & AI Hackathon — Databricks Backend Pipeline
# MAGIC ---
# MAGIC 
# MAGIC **Business Use Case:** An online store wants to recommend products to users based on their past purchases.
# MAGIC 
# MAGIC **Problem Statement Prerequisites:**
# MAGIC - ✅ Create a user-product interaction dataset (Step 1)
# MAGIC - ✅ Build a user-product matrix (Step 4)
# MAGIC - ✅ Apply collaborative filtering (NMF) + similarity-based logic (Steps 5-9)
# MAGIC - ✅ Generate product recommendations (Step 6)
# MAGIC 
# MAGIC **Outcome:** Recommendation systems improve customer experience by suggesting relevant products. This increases customer engagement, boosts sales, and helps businesses personalize their platforms.
# MAGIC 
# MAGIC **Architecture:** scikit-learn NMF (Non-negative Matrix Factorization) + PySpark Content-Based Similarity
# MAGIC 
# MAGIC > **Note:** This pipeline uses scikit-learn NMF instead of Spark MLlib ALS so it runs on
# MAGIC > **any** Databricks compute tier, including Serverless. The dataset size (500 users × 200
# MAGIC > products) is ideal for in-memory factorization.
# MAGIC 
# MAGIC **Pipeline Steps:**
# MAGIC 1. Data Loading
# MAGIC 2. Data Preprocessing & Cleaning
# MAGIC 3. Exploratory Data Analysis
# MAGIC 4. Feature Engineering (User-Product Matrix)
# MAGIC 5. NMF Collaborative Filtering Model (scikit-learn)
# MAGIC 6. Top-N Recommendations Generation
# MAGIC 7. Popular Products by Category
# MAGIC 8. Similar Products (Content-Based)
# MAGIC 9. Complementary / Accessory Products (Cross-Category)
# MAGIC 10. Top Rated Products
# MAGIC 11. Results Export to JSON

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0: Environment Setup

# COMMAND ----------

# Import all required libraries
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, IntegerType, StringType,
    FloatType, DoubleType, TimestampType
)
from pyspark.sql.window import Window
import json
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.metrics import mean_squared_error, mean_absolute_error

# Initialize Spark session (Databricks provides this automatically)
# Uncomment below if running outside Databricks:
# spark = SparkSession.builder.appName("ProductRecommendation").getOrCreate()

print("✅ Environment ready — Spark version:", spark.version)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Data Loading
# MAGIC Load the three CSV datasets: Users, Products, Interactions.
# MAGIC
# MAGIC > **Note:** Upload CSV files to `/Workspace/Users/<you>/CloudFront_Hackathon/datasets/` before running.

# COMMAND ----------

# ── Define file paths (Workspace) ──────────────────────────────────────────
USERS_PATH      = "/Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/datasets/users.csv"
PRODUCTS_PATH   = "/Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/datasets/products.csv"
INTERACTIONS_PATH = "/Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/datasets/interactions.csv"

# ── Load Users ──────────────────────────────────────────────────────────────
users_schema = StructType([
    StructField("user_id", IntegerType(), False),
    StructField("age_group", StringType(), True),
    StructField("location", StringType(), True),
    StructField("preferred_category", StringType(), True),
    StructField("membership_type", StringType(), True),
    StructField("signup_date", StringType(), True),
])

df_users = (
    spark.read
    .option("header", "true")
    .schema(users_schema)
    .csv(USERS_PATH)
)
print(f"👤 Users loaded: {df_users.count()} rows")
df_users.show(5)

# COMMAND ----------

# ── Load Products ───────────────────────────────────────────────────────────
products_schema = StructType([
    StructField("product_id", IntegerType(), False),
    StructField("product_name", StringType(), True),
    StructField("category", StringType(), True),
    StructField("sub_category", StringType(), True),
    StructField("brand", StringType(), True),
    StructField("price", FloatType(), True),
    StructField("price_range", StringType(), True),
    StructField("avg_rating", FloatType(), True),
    StructField("rating_count", IntegerType(), True),
    StructField("stock", IntegerType(), True),
])

df_products = (
    spark.read
    .option("header", "true")
    .schema(products_schema)
    .csv(PRODUCTS_PATH)
)
print(f"📦 Products loaded: {df_products.count()} rows")
df_products.show(5)

# COMMAND ----------

# ── Load Interactions ───────────────────────────────────────────────────────
interactions_schema = StructType([
    StructField("user_id", IntegerType(), False),
    StructField("product_id", IntegerType(), False),
    StructField("interaction_type", StringType(), True),
    StructField("interaction_score", IntegerType(), True),
    StructField("rating", StringType(), True),
    StructField("review_sentiment", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("session_id", StringType(), True),
])

df_interactions = (
    spark.read
    .option("header", "true")
    .schema(interactions_schema)
    .csv(INTERACTIONS_PATH)
)
print(f"🔄 Interactions loaded: {df_interactions.count()} rows")
df_interactions.show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Data Preprocessing & Cleaning

# COMMAND ----------

# ── Clean interactions ──────────────────────────────────────────────────────

# Convert rating column: empty strings → null, then cast to float
df_interactions_clean = (
    df_interactions
    .withColumn("rating",
        F.when(F.col("rating") == "", None)
         .otherwise(F.col("rating").cast(FloatType()))
    )
    .withColumn("review_sentiment",
        F.when(F.col("review_sentiment") == "", None)
         .otherwise(F.col("review_sentiment"))
    )
    .withColumn("timestamp", F.to_timestamp("timestamp", "yyyy-MM-dd HH:mm:ss"))
    # Drop rows with null user_id or product_id
    .dropna(subset=["user_id", "product_id"])
    # Remove duplicate interactions within the same session
    .dropDuplicates(["user_id", "product_id", "interaction_type", "session_id"])
)

print(f"🧹 Cleaned interactions: {df_interactions_clean.count()} rows")
df_interactions_clean.printSchema()

# COMMAND ----------

# ── Clean products ──────────────────────────────────────────────────────────
df_products_clean = (
    df_products
    .dropna(subset=["product_id", "product_name"])
    .withColumn("price", F.when(F.col("price") < 0, 0).otherwise(F.col("price")))
    .withColumn("avg_rating",
        F.when(F.col("avg_rating") > 5, 5.0)
         .when(F.col("avg_rating") < 0, 0.0)
         .otherwise(F.col("avg_rating"))
    )
)

# ── Clean users ─────────────────────────────────────────────────────────────
df_users_clean = df_users.dropna(subset=["user_id"])

print(f"📦 Clean products: {df_products_clean.count()}")
print(f"👤 Clean users: {df_users_clean.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Exploratory Data Analysis

# COMMAND ----------

# ── Interaction type distribution ───────────────────────────────────────────
print("📊 Interaction Type Distribution:")
df_interactions_clean.groupBy("interaction_type").count().orderBy(F.desc("count")).show()

# ── Products per category ──────────────────────────────────────────────────
print("📊 Products per Category:")
df_products_clean.groupBy("category").count().orderBy(F.desc("count")).show()

# ── User membership distribution ───────────────────────────────────────────
print("📊 Membership Distribution:")
df_users_clean.groupBy("membership_type").count().orderBy(F.desc("count")).show()

# ── Average price per category ─────────────────────────────────────────────
print("📊 Average Price per Category:")
df_products_clean.groupBy("category").agg(
    F.round(F.avg("price"), 2).alias("avg_price"),
    F.round(F.avg("avg_rating"), 2).alias("avg_rating"),
    F.count("*").alias("product_count")
).orderBy(F.desc("avg_price")).show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Feature Engineering
# MAGIC Build the user-product interaction matrix with aggregated scores.

# COMMAND ----------

# ── Aggregate interaction scores per (user, product) pair ───────────────────
# This creates the implicit feedback matrix for NMF

df_user_product = (
    df_interactions_clean
    .groupBy("user_id", "product_id")
    .agg(
        F.sum("interaction_score").alias("total_score"),       # Weighted interaction
        F.count("*").alias("interaction_count"),               # Frequency
        F.max("rating").alias("max_rating"),                   # Best rating given
        F.collect_set("interaction_type").alias("interaction_types"),  # Types of interaction
    )
    # Normalize score: combine interaction score with rating if available
    .withColumn("final_score",
        F.when(F.col("max_rating").isNotNull(),
            (F.col("total_score") * 0.7 + F.col("max_rating") * 0.3))
         .otherwise(F.col("total_score").cast(DoubleType()))
    )
)

print(f"📐 User-Product Matrix: {df_user_product.count()} unique pairs")
df_user_product.show(10)

# COMMAND ----------

# ── Verify score distribution ──────────────────────────────────────────────
print("📊 Score Statistics:")
df_user_product.select(
    F.min("final_score").alias("min"),
    F.max("final_score").alias("max"),
    F.round(F.mean("final_score"), 2).alias("mean"),
    F.round(F.stddev("final_score"), 2).alias("stddev"),
).show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: NMF Collaborative Filtering Model (scikit-learn)
# MAGIC 
# MAGIC We use **Non-negative Matrix Factorization (NMF)** from scikit-learn instead of Spark
# MAGIC MLlib ALS. NMF is conceptually equivalent — it decomposes the user-product matrix into
# MAGIC two low-rank non-negative matrices W (users × factors) and H (factors × products).
# MAGIC 
# MAGIC This approach works on **all Databricks compute tiers** including Serverless.

# COMMAND ----------

# ── Convert user-product matrix to pandas ──────────────────────────────────
df_nmf_input = (
    df_user_product
    .select("user_id", "product_id", "final_score")
    .na.drop()
)

print(f"📊 NMF input: {df_nmf_input.count()} rows")
df_nmf_input.show(5)

# Convert to pandas pivot table (users × products)
pdf_scores = df_nmf_input.toPandas()
pivot = pdf_scores.pivot(index="user_id", columns="product_id", values="final_score").fillna(0)

all_user_ids = pivot.index.tolist()       # ordered user IDs
all_product_ids = pivot.columns.tolist()  # ordered product IDs
R = pivot.values.astype(np.float64)       # rating matrix

print(f"📐 Rating matrix shape: {R.shape} (users × products)")

# COMMAND ----------

# ── Train-test masking (80/20) ─────────────────────────────────────────────
np.random.seed(42)
mask = np.random.rand(*R.shape) < 0.8   # True = train, False = test
non_zero = R > 0                         # Only evaluate where interactions exist

train_matrix = R.copy()
train_matrix[~mask & non_zero] = 0       # Zero-out test entries

print(f"   Training entries: {int((mask & non_zero).sum())}")
print(f"   Test entries:     {int((~mask & non_zero).sum())}")

# COMMAND ----------

# ── Build NMF Model ────────────────────────────────────────────────────────
NUM_FACTORS = 20   # Latent factors (equivalent to ALS rank)

nmf_model = NMF(
    n_components=NUM_FACTORS,
    init="nndsvda",           # Non-negative Double SVD — robust initializer
    max_iter=300,
    random_state=42,
    alpha_W=0.1,              # Regularization on W (users)
    alpha_H=0.1,              # Regularization on H (products)
    l1_ratio=0.0,             # Pure L2 regularization
)

print("🚀 Training NMF model...")
W = nmf_model.fit_transform(train_matrix)   # users  × factors
H = nmf_model.components_                   # factors × products
print(f"✅ NMF training complete!  W={W.shape}  H={H.shape}")
print(f"   Reconstruction error: {nmf_model.reconstruction_err_:.4f}")

# ── Predicted scores ───────────────────────────────────────────────────────
R_pred = W @ H   # Full predicted rating matrix

# COMMAND ----------

# ── Evaluate on held-out test entries ──────────────────────────────────────
test_mask = ~mask & non_zero
y_true = R[test_mask]
y_pred = R_pred[test_mask]

rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
mae  = float(mean_absolute_error(y_true, y_pred))

print(f"📈 Model RMSE: {rmse:.4f}")
print(f"📈 Model MAE:  {mae:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Generate Top-5 Recommendations per User

# COMMAND ----------

# ── Generate top 5 recommendations for ALL users ──────────────────────────
NUM_RECOMMENDATIONS = 5

rec_rows = []
for i, uid in enumerate(all_user_ids):
    scores = R_pred[i]              # predicted scores for this user
    interacted = set(np.where(R[i] > 0)[0])  # indices already interacted
    # Rank all products, exclude already-interacted
    ranked_indices = np.argsort(-scores)
    count = 0
    for idx in ranked_indices:
        if idx in interacted:
            continue
        rec_rows.append((int(uid), int(all_product_ids[idx]), round(float(scores[idx]), 3)))
        count += 1
        if count >= NUM_RECOMMENDATIONS:
            break

print(f"🎯 Generated {len(rec_rows)} recommendations for {len(all_user_ids)} users")

# COMMAND ----------

# ── Convert recommendations to Spark DataFrame & join product details ──────
df_recs_flat = spark.createDataFrame(rec_rows, ["user_id", "product_id", "predicted_score"])

df_recs_detailed = (
    df_recs_flat
    .join(df_products_clean, on="product_id", how="left")
    .select(
        "user_id",
        "product_id",
        "product_name",
        "category",
        "sub_category",
        "brand",
        "price",
        "avg_rating",
        "predicted_score",
    )
    .orderBy("user_id", F.desc("predicted_score"))
)

print("🎯 Top-5 Recommendations (sample):")
df_recs_detailed.show(25, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Popular Products by Category

# COMMAND ----------

# ── Compute popularity score per product ────────────────────────────────────
df_popularity = (
    df_interactions_clean
    .groupBy("product_id")
    .agg(
        F.sum("interaction_score").alias("popularity_score"),
        F.count("*").alias("total_interactions"),
        F.countDistinct("user_id").alias("unique_users"),
    )
    .join(df_products_clean, on="product_id", how="left")
)

# ── Top popular products per category ──────────────────────────────────────
window_cat = Window.partitionBy("category").orderBy(F.desc("popularity_score"))

df_popular_by_cat = (
    df_popularity
    .withColumn("rank", F.row_number().over(window_cat))
    .filter(F.col("rank") <= 8)
    .select(
        "category", "rank", "product_id", "product_name",
        "brand", "price", "avg_rating", "popularity_score",
        "total_interactions", "unique_users",
    )
    .orderBy("category", "rank")
)

print("🔥 Popular Products by Category:")
df_popular_by_cat.show(48, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Similar Products (Content-Based)

# COMMAND ----------

# ── Item-based similarity using category + sub_category matching ───────────
# For each product, find top 5 similar products in the same sub-category
# ranked by avg_rating and interaction volume

df_prod_with_stats = (
    df_products_clean
    .join(
        df_interactions_clean.groupBy("product_id")
            .agg(F.sum("interaction_score").alias("total_engagement")),
        on="product_id",
        how="left"
    )
    .fillna(0, subset=["total_engagement"])
)

# Self-join on sub_category to find similar items
df_similar = (
    df_prod_with_stats.alias("a")
    .join(
        df_prod_with_stats.alias("b"),
        (F.col("a.sub_category") == F.col("b.sub_category")) &
        (F.col("a.product_id") != F.col("b.product_id")),
        how="inner"
    )
    .select(
        F.col("a.product_id").alias("source_product_id"),
        F.col("a.product_name").alias("source_product_name"),
        F.col("b.product_id").alias("similar_product_id"),
        F.col("b.product_name").alias("similar_product_name"),
        F.col("b.category").alias("category"),
        F.col("b.brand").alias("brand"),
        F.col("b.price").alias("price"),
        F.col("b.avg_rating").alias("avg_rating"),
        F.col("b.total_engagement").alias("engagement"),
    )
)

# Rank similar products
window_sim = Window.partitionBy("source_product_id").orderBy(
    F.desc("avg_rating"), F.desc("engagement")
)

df_similar_ranked = (
    df_similar
    .withColumn("sim_rank", F.row_number().over(window_sim))
    .filter(F.col("sim_rank") <= 5)
    .orderBy("source_product_id", "sim_rank")
)

print("🔗 Similar Products (sample for product_id 1-5):")
df_similar_ranked.filter(F.col("source_product_id").isin([1, 2, 3, 4, 5])).show(25, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 9: Complementary / Accessory Products (Cross-Category)
# MAGIC 
# MAGIC For each product, find complementary products from related sub-categories.
# MAGIC E.g., Laptops → Headphones, Smartphones → Smartwatches, T-Shirts → Jeans.

# COMMAND ----------

# ── Cross-category complementary mapping (pure DataFrame — no UDF) ─────
# Uses a mapping DataFrame instead of broadcast+UDF for full Serverless compatibility

COMPLEMENTARY_MAP = {
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

# Build a Spark DataFrame from the mapping (no UDF / broadcast needed)
comp_rows = [(src, tgt) for src, targets in COMPLEMENTARY_MAP.items() for tgt in targets]
df_comp_map = spark.createDataFrame(comp_rows, ["source_sub_category", "target_sub_category"])

# Join products with their complementary sub-categories
df_comp_exploded = (
    df_prod_with_stats
    .select(
        F.col("product_id").alias("source_product_id"),
        F.col("product_name").alias("source_product_name"),
        F.col("sub_category").alias("source_sub_category"),
    )
    .join(df_comp_map, on="source_sub_category", how="inner")
)

df_complementary = (
    df_comp_exploded.alias("a")
    .join(
        df_prod_with_stats.alias("b"),
        F.col("a.target_sub_category") == F.col("b.sub_category"),
        how="inner"
    )
    .select(
        F.col("a.source_product_id"),
        F.col("a.source_product_name"),
        F.col("b.product_id").alias("comp_product_id"),
        F.col("b.product_name").alias("comp_product_name"),
        F.col("b.category").alias("category"),
        F.col("b.sub_category").alias("sub_category"),
        F.col("b.brand").alias("brand"),
        F.col("b.price").alias("price"),
        F.col("b.avg_rating").alias("avg_rating"),
        F.col("b.total_engagement").alias("engagement"),
    )
)

# Rank complementary products per source product
window_comp = Window.partitionBy("source_product_id").orderBy(
    F.desc("avg_rating"), F.desc("engagement")
)

df_complementary_ranked = (
    df_complementary
    .withColumn("comp_rank", F.row_number().over(window_comp))
    .filter(F.col("comp_rank") <= 5)
    .orderBy("source_product_id", "comp_rank")
)

print("🎯 Complementary Products (sample for product_id 1-5):")
df_complementary_ranked.filter(F.col("source_product_id").isin([1, 2, 3, 4, 5])).show(25, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 10: Top Rated Products

# COMMAND ----------

# ── Top 20 highest-rated products with sufficient reviews ──────────────────
df_top_rated = (
    df_products_clean
    .filter(F.col("rating_count") >= 50)  # Minimum review threshold
    .orderBy(F.desc("avg_rating"), F.desc("rating_count"))
    .limit(20)
    .select(
        "product_id", "product_name", "category", "brand",
        "price", "avg_rating", "rating_count",
    )
)

print("⭐ Top 20 Rated Products:")
df_top_rated.show(20, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 11: Export Results to JSON (for Frontend)
# MAGIC
# MAGIC These JSON files can be downloaded from DBFS and placed in the frontend `data/` folder.

# COMMAND ----------

# ── Helper: Convert Spark DF to JSON-serializable list ─────────────────────
def df_to_json_list(df):
    """Convert a Spark DataFrame to a list of dictionaries."""
    return [row.asDict() for row in df.collect()]

# ── Export recommendations grouped by user_id ──────────────────────────────
recs_list = df_to_json_list(df_recs_detailed)
recs_by_user = {}
for row in recs_list:
    uid = str(row["user_id"])
    if uid not in recs_by_user:
        recs_by_user[uid] = []
    recs_by_user[uid].append({
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "category": row["category"],
        "sub_category": row["sub_category"],
        "brand": row["brand"],
        "price": float(row["price"]) if row["price"] else 0,
        "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else 0,
        "predicted_score": float(row["predicted_score"]) if row["predicted_score"] else 0,
    })

# Save to Workspace
OUTPUT_DIR = "/Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/output"

dbutils.fs.put(
    f"{OUTPUT_DIR}/recommendations.json",
    json.dumps(recs_by_user, indent=2),
    overwrite=True
)
print("✅ recommendations.json exported")

# COMMAND ----------

# ── Export popular by category ─────────────────────────────────────────────
popular_list = df_to_json_list(df_popular_by_cat)
popular_by_cat = {}
for row in popular_list:
    cat = row["category"]
    if cat not in popular_by_cat:
        popular_by_cat[cat] = []
    popular_by_cat[cat].append({
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "brand": row["brand"],
        "price": float(row["price"]) if row["price"] else 0,
        "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else 0,
        "popularity_score": int(row["popularity_score"]) if row["popularity_score"] else 0,
    })

dbutils.fs.put(
    f"{OUTPUT_DIR}/popular_by_category.json",
    json.dumps(popular_by_cat, indent=2),
    overwrite=True
)
print("✅ popular_by_category.json exported")

# COMMAND ----------

# ── Export similar products ────────────────────────────────────────────────
similar_list = df_to_json_list(df_similar_ranked)
similar_map = {}
for row in similar_list:
    src = str(row["source_product_id"])
    if src not in similar_map:
        similar_map[src] = []
    similar_map[src].append({
        "product_id": row["similar_product_id"],
        "product_name": row["similar_product_name"],
        "category": row["category"],
        "brand": row["brand"],
        "price": float(row["price"]) if row["price"] else 0,
        "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else 0,
    })

dbutils.fs.put(
    f"{OUTPUT_DIR}/similar_products.json",
    json.dumps(similar_map, indent=2),
    overwrite=True
)
print("✅ similar_products.json exported")

# COMMAND ----------

# ── Export complementary / accessory products ───────────────────────────
comp_list = df_to_json_list(df_complementary_ranked)
comp_map = {}
for row in comp_list:
    src = str(row["source_product_id"])
    if src not in comp_map:
        comp_map[src] = []
    comp_map[src].append({
        "product_id": row["comp_product_id"],
        "product_name": row["comp_product_name"],
        "category": row["category"],
        "sub_category": row["sub_category"],
        "brand": row["brand"],
        "price": float(row["price"]) if row["price"] else 0,
        "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else 0,
    })

dbutils.fs.put(
    f"{OUTPUT_DIR}/complementary_products.json",
    json.dumps(comp_map, indent=2),
    overwrite=True
)
print("✅ complementary_products.json exported")

# COMMAND ----------

# ── Export top rated ───────────────────────────────────────────────────────
top_rated_list = df_to_json_list(df_top_rated)
top_rated_out = [
    {
        "product_id": r["product_id"],
        "product_name": r["product_name"],
        "category": r["category"],
        "brand": r["brand"],
        "price": float(r["price"]) if r["price"] else 0,
        "avg_rating": float(r["avg_rating"]) if r["avg_rating"] else 0,
        "rating_count": int(r["rating_count"]) if r["rating_count"] else 0,
    }
    for r in top_rated_list
]

dbutils.fs.put(
    f"{OUTPUT_DIR}/top_rated.json",
    json.dumps(top_rated_out, indent=2),
    overwrite=True
)
print("✅ top_rated.json exported")

# COMMAND ----------

# ── Export products catalog ────────────────────────────────────────────────
products_out = df_to_json_list(
    df_products_clean.select(
        "product_id", "product_name", "category", "sub_category",
        "brand", "price", "price_range", "avg_rating", "rating_count"
    )
)

dbutils.fs.put(
    f"{OUTPUT_DIR}/products.json",
    json.dumps(products_out, indent=2),
    overwrite=True
)
print("✅ products.json exported")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Pipeline Complete!
# MAGIC
# MAGIC **Business Use Case:** Product Recommendation System for an Online Store
# MAGIC 
# MAGIC **What we built:**
# MAGIC - User-product interaction dataset with 500 users, 200 products, 15K interactions
# MAGIC - User-product matrix via aggregated interaction scores
# MAGIC - NMF collaborative filtering model (20 latent factors, scikit-learn)
# MAGIC - Content-based similar products (same sub-category)
# MAGIC - Cross-category complementary/accessory products
# MAGIC
# MAGIC **Exported files** (in Workspace → `CloudFront_Hackathon/output/`):
# MAGIC
# MAGIC | File | Description |
# MAGIC |------|-------------|
# MAGIC | `recommendations.json` | Top-5 NMF recommendations per user |
# MAGIC | `popular_by_category.json` | Popular products grouped by category |
# MAGIC | `similar_products.json` | Similar products for each product |
# MAGIC | `complementary_products.json` | Cross-category accessory products |
# MAGIC | `top_rated.json` | Top 20 highest-rated products |
# MAGIC | `products.json` | Full product catalog |
# MAGIC
# MAGIC **Next Steps:**
# MAGIC 1. JSON files are saved to Workspace `output/` folder
# MAGIC 2. The local Flask API server reads from `frontend/data/`
# MAGIC 3. Download output JSONs → place in `frontend/data/` → start `api_server.py`
# MAGIC 4. Frontend connects to the API at `http://localhost:5000`

# COMMAND ----------

# ── Final Summary ──────────────────────────────────────────────────────────
print("=" * 60)
print("   🛒 RECOMMENDATION SYSTEM — PIPELINE SUMMARY")
print("=" * 60)
print(f"   Users:         {df_users_clean.count()}")
print(f"   Products:      {df_products_clean.count()}")
print(f"   Interactions:  {df_interactions_clean.count()}")
print(f"   Matrix Pairs:  {df_user_product.count()}")
print(f"   NMF Factors:   {NUM_FACTORS}")
print(f"   Model RMSE:    {rmse:.4f}")
print(f"   Model MAE:     {mae:.4f}")
print(f"   Recommendations Generated for {len(all_user_ids)} users")
print("=" * 60)
