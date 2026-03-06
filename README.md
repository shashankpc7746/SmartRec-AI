# 🛒 SmartRec AI — Product Recommendation System

> **CloudFront Data & AI Campus Drive Hackathon**  
> AI-powered product recommendations using Databricks, PySpark, scikit-learn NMF, and a modern web frontend.

---

## � Business Use Case

**Problem Statement:** An online store wants to recommend products to users based on their past purchases.

**Prerequisites Covered:**
- ✅ User-product interaction dataset (500 users, 200 products, 15K interactions)
- ✅ User-product matrix (aggregated interaction scores with rating fusion)
- ✅ Collaborative filtering (NMF) + similarity-based logic
- ✅ Cross-category complementary/accessory recommendations
- ✅ Product recommendations with time-decay weighted personalization

**Outcome:** The recommendation system improves customer experience by suggesting relevant products. This increases customer engagement, boosts sales, and helps businesses personalize their platforms.

---

## 📁 Project Structure

```
HackThon/
├── backend/
│   ├── recommendation_notebook.py   # Databricks notebook (PySpark + NMF pipeline)
│   ├── api_server.py                # Flask REST API server (serves data to frontend)
│   ├── generate_datasets.py         # Dataset generator script
│   └── data/
│       ├── users.csv                # 500 users with demographics
│       ├── products.csv             # 200 products across 6 categories
│       └── interactions.csv         # 15,000 user-product interactions
│
├── frontend/
│   ├── index.html                   # Main UI (onboarding + feed + modals)
│   ├── css/
│   │   └── styles.css               # Production-grade styling
│   ├── js/
│   │   └── app.js                   # Frontend app (calls API or falls back to static)
│   └── data/
│       ├── recommendations.json     # Per-user NMF recommendations
│       ├── popular_by_category.json # Popular products per category
│       ├── similar_products.json    # Item-based similarity results
│       ├── complementary_products.json # Cross-category accessories
│       ├── top_rated.json           # Top 20 highest-rated products
│       └── products.json            # Full product catalog
│
└── README.md
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATABRICKS BACKEND                    │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │  Users   │  │ Products │  │   Interactions        │  │
│  │  (CSV)   │  │  (CSV)   │  │   (CSV)               │  │
│  └────┬─────┘  └────┬─────┘  └──────────┬────────────┘  │
│       └──────────────┼──────────────────┘                │
│                      ▼                                   │
│          ┌───────────────────────┐                       │
│          │  Data Preprocessing   │                       │
│          │  Feature Engineering  │                       │
│          └───────────┬───────────┘                       │
│                      ▼                                   │
│          ┌───────────────────────┐                       │
│          │   NMF Collaborative    │                       │
│          │   Filtering (sklearn)  │                       │
│          └───────────┬───────────┘                       │
│                      ▼                                   │
│          ┌───────────────────────┐                       │
│          │  JSON Export to DBFS  │                       │
│          └───────────┬───────────┘                       │
└──────────────────────┼──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (Local)                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │               index.html                        │    │
│  │  ┌──────────┐ ┌────────┐ ┌─────────┐ ┌───────┐ │    │
│  │  │ Recommend│ │Popular │ │Top Rated│ │Similar│ │    │
│  │  │ ations   │ │Products│ │Products │ │Items  │ │    │
│  │  └──────────┘ └────────┘ └─────────┘ └───────┘ │    │
│  └─────────────────────────────────────────────────┘    │
│               ▲ Reads from data/*.json                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 How to Run (Complete Step-by-Step Guide)

### Step 1: Generate Datasets (Local)

```bash
cd HackThon
python backend/generate_datasets.py
```

This creates:
- 3 CSV files in `backend/data/` (users, products, interactions)
- 6 JSON files in `frontend/data/` (recommendations, popular, similar, complementary, top_rated, products)

### Step 2: Run the Databricks Notebook

> **For the hackathon demo:** The `generate_datasets.py` already creates realistic JSON files that simulate the Databricks output, so the frontend works immediately without Databricks. Steps 2A-2F are for the actual Databricks pipeline.

#### 2A: Create a Databricks Workspace
- Log in to [Databricks Community Edition](https://community.cloud.databricks.com/) (free) or your enterprise workspace
- Create a cluster — **any compute tier works** including Serverless (the notebook uses scikit-learn NMF, not Spark MLlib)

#### 2B: Upload CSV Files to Workspace
1. In Databricks, navigate to **Workspace** → **Users** → `shashankpc7746@gmail.com`
2. Create folder structure: `CloudFront_Hackathon/datasets/`
3. Upload these 3 CSV files from `backend/data/`:
   - `users.csv`
   - `products.csv`
   - `interactions.csv`

The notebook reads from:
```
/Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/datasets/
```

#### 2C: Import the Notebook
1. In the sidebar, go to **Workspace** → **Users** → your email
2. Click **Import** → choose **File**
3. Select `backend/recommendation_notebook.py`
4. Databricks will auto-detect the `# Databricks notebook source` header and the `# COMMAND ----------` cell separators

#### 2D: Run the Notebook
1. Attach the notebook to your running cluster
2. Click **Run All** or run each cell sequentially (Shift+Enter)
3. Pipeline steps:
   - Steps 1-3: Load & clean data, EDA
   - Step 4: Build user-product interaction matrix
   - Step 5: Train NMF model (collaborative filtering — works on Serverless)
   - Step 6: Generate top-5 recommendations per user
   - Steps 7-10: Popular, similar, complementary, top-rated products
   - Step 11: Export 6 JSON files to DBFS

#### 2E: Download JSON Output
1. After the notebook completes, JSON files are saved to:
   `/Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/output/`
2. Download all 6 JSON files and place them in `frontend/data/`
3. Or use Databricks CLI:
```bash
databricks workspace export-dir /Workspace/Users/shashankpc7746@gmail.com/CloudFront_Hackathon/output/ frontend/data/
```

#### 2F: Verify JSON Files
Ensure `frontend/data/` contains all 6 files:
- `products.json`
- `recommendations.json`
- `popular_by_category.json`  
- `similar_products.json`
- `complementary_products.json`
- `top_rated.json`

### Step 3: Start the API Server

```bash
pip install flask flask-cors
python backend/api_server.py
```

This starts a REST API at `http://localhost:5000` that serves the JSON data.

**API Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `GET /api/products` | Full product catalog |
| `GET /api/recommendations` | All user recommendations |
| `GET /api/recommendations/<uid>` | Recommendations for one user |
| `GET /api/popular` | Popular products by category |
| `GET /api/similar/<pid>` | Similar products for a product |
| `GET /api/complementary/<pid>` | Complementary/accessory products |
| `GET /api/toprated` | Top rated products |
| `GET /api/health` | Health check |
| `POST /api/reload` | Reload data files from disk |

### Step 4: Launch the Frontend

Option A — **VS Code Live Server:**
1. Install the "Live Server" extension in VS Code
2. Right-click `frontend/index.html` → "Open with Live Server"

Option B — **Python HTTP Server:**
```bash
cd frontend
python -m http.server 8000
```
Then open `http://localhost:8000` in your browser.

> The frontend auto-detects the API server. If the API is running on port 5000, it uses
> live API calls. If not, it falls back to reading static JSON files from `data/`.

### Step 5: Use the Application
1. **Onboarding:** Enter your name and pick at least 2 preferred categories
2. **Browse:** See personalized recommendations + category sections
3. **Interact:** Click products, add to cart, wishlist — recommendations update in real-time
4. **Profile:** Click your name in the navbar to edit preferred categories
5. **Recommendations improve** as you interact more — recent interactions weigh heavier

---

## 🔬 ML Pipeline Details

### Datasets

| Dataset | Rows | Description |
|---------|------|-------------|
| Users | 500 | Demographics: age, location, preferred category, membership |
| Products | 200 | 6 categories, 30+ sub-categories, pricing, ratings |
| Interactions | 15,000 | Views, clicks, add-to-cart, purchases with weighted scores |

### Interaction Score Weights

| Action | Weight |
|--------|--------|
| View | 1 |
| Click | 2 |
| Add to Cart | 3 |
| Purchase | 5 |

### NMF Model Configuration

| Parameter | Value |
|-----------|-------|
| Latent Factors (n_components) | 20 |
| Max Iterations | 300 |
| Initialization | NNDSVDA |
| Regularization (alpha_W, alpha_H) | 0.1 |
| L1 Ratio | 0.0 (pure L2) |
| Serverless Compatible | ✅ Yes |

### Recommendation Features

| Feature | Method |
|---------|--------|
| Personalized Recommendations | NMF Collaborative Filtering (scikit-learn) |
| Time-Decay Weighting | Recent interactions weigh more via exponential decay |
| Popular Products | Weighted interaction score aggregation |
| Similar Products | Content-based (sub-category matching) |
| Complementary/Accessories | Cross-category mapping (e.g., Laptop → Headphones) |
| Top Rated | Rating + review count threshold |

---

## 🔗 Frontend ↔ Backend Connection

The system uses an **offline-first** architecture optimized for hackathon demos:

1. **Databricks pipeline** processes data and trains the NMF model
2. **Results exported** as JSON files to Workspace output folder
3. **JSON files downloaded** to `frontend/data/`
4. **Flask API server** serves the JSON data as REST endpoints on port 5000
5. **Frontend calls** the API via `fetch()` — auto-falls back to static files if API is down

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend ML | PySpark, scikit-learn NMF, Databricks |
| API Server | Flask, flask-cors (Python) |
| Data Processing | PySpark DataFrames |
| Dataset Generation | Python (csv, json, random) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Styling | Custom CSS with Inter font |
| Data Format | JSON (exported from Spark) |

---

## 📊 Product Categories & Complementary Mapping

- **Electronics** — Smartphones, Laptops, Headphones, Tablets, Smartwatches
- **Fashion** — T-Shirts, Jeans, Sneakers, Jackets, Dresses
- **Books** — Fiction, Non-Fiction, Sci-Fi, Self-Help, Comics
- **Home & Kitchen** — Cookware, Furniture, Decor, Appliances, Storage
- **Sports** — Cricket, Football, Fitness, Yoga, Running
- **Beauty** — Skincare, Haircare, Makeup, Fragrance, Grooming

**Cross-category examples:** Laptops → Headphones/Tablets, Sneakers → Running/Jeans, Fitness → Yoga/Smartwatches

---

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| Blank page on frontend | Make sure JSON files exist in `frontend/data/`. Run `python backend/generate_datasets.py` |
| Databricks import fails | Ensure the `.py` file starts with `# Databricks notebook source` |
| DBFS upload issues | Use Workspace path: `/Workspace/Users/<you>/CloudFront_Hackathon/datasets/` |
| API server not starting | Run `pip install flask flask-cors` then `python backend/api_server.py` |
| Frontend can't reach API | Ensure API is on port 5000; frontend auto-falls back to static JSON |
| Cluster can't start | Use Databricks Runtime 13.x+ (or Serverless) with at least 2 cores |
| Recommendations not updating | Click a few products — recommendations update after each interaction |

---

## 👥 Team

CloudFront Data & AI Hackathon Entry
