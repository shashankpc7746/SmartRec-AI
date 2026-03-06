/**
 * ═══════════════════════════════════════════════════════════════════════════
 *  SmartRec AI — Product Recommendation System
 *  Business Use Case: Recommend products to users based on past purchases
 *
 *  Flow:
 *    1. Onboarding: user enters name + picks preferred categories
 *    2. Main feed:
 *       - "Recommended For You" — weighted by ALL past interactions
 *         (recent interactions carry higher weight, older ones contribute less)
 *       - One section per chosen category showing 4 products each
 *    3. Interactions (click/like/cart) update recommendations:
 *       - Uses time-decay weighting across entire interaction history
 *       - Includes both similar + complementary/accessory products
 *    4. Product detail modal with "Similar" and "Accessories" sections
 *    5. Cart & Wishlist sidebars
 *    6. Profile panel to edit preferred categories
 *
 *  Data pipeline: Databricks PySpark ALS → JSON exports → Frontend reads
 *  All user state is stored in localStorage so it survives refresh.
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ── Config ─────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:5000/api";  // Flask API server
const DATA = "data";                            // Fallback for static JSON

// Category metadata
const CAT_META = {
    "Electronics":    { icon: "💻", strip: "strip-electronics", badge: "badge-electronics", emoji: "📱" },
    "Fashion":        { icon: "👗", strip: "strip-fashion",     badge: "badge-fashion",     emoji: "👟" },
    "Books":          { icon: "📚", strip: "strip-books",       badge: "badge-books",       emoji: "📖" },
    "Home & Kitchen": { icon: "🏠", strip: "strip-home",        badge: "badge-home",        emoji: "🍳" },
    "Sports":         { icon: "⚽", strip: "strip-sports",      badge: "badge-sports",      emoji: "🏃" },
    "Beauty":         { icon: "💄", strip: "strip-beauty",      badge: "badge-beauty",      emoji: "✨" },
};

// ── App State ──────────────────────────────────────────────────────────────
let store = {
    products: [],
    popularByCategory: {},
    similarProducts: {},
    complementaryProducts: {},
    topRated: [],
};

// Persistent user state (localStorage)
function loadUser() {
    const raw = localStorage.getItem("smartrec_user");
    if (!raw) return null;
    return JSON.parse(raw);
}
function saveUser(user) {
    localStorage.setItem("smartrec_user", JSON.stringify(user));
}
function clearUser() {
    localStorage.removeItem("smartrec_user");
}

// Default user shape
function newUser(name, categories) {
    return {
        name,
        categories,
        cart: [],       // array of product_id
        liked: [],      // array of product_id
        lastInteracted: null,  // product_id of last click/like/cart
        interactions: [],      // [{product_id, type, timestamp}]
    };
}

// ═══════════════════════════════════════════════════════════════════════════
//  DATA LOADING
// ═══════════════════════════════════════════════════════════════════════════

async function loadJSON(file) {
    const r = await fetch(`${DATA}/${file}`);
    if (!r.ok) throw new Error(`Failed to load ${file}`);
    return r.json();
}

let useAPI = false; // Set to true once API health check passes

async function loadAllData() {
    // Try API first; if unreachable, fall back to static JSON files
    try {
        const health = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
        if (health.ok) useAPI = true;
    } catch (_) {
        useAPI = false;
    }

    if (useAPI) {
        console.log("🔗 Connected to API server at", API_BASE);
        const [products, popular, similar, complementary, topRated] = await Promise.all([
            fetch(`${API_BASE}/products`).then(r => r.json()),
            fetch(`${API_BASE}/popular`).then(r => r.json()),
            fetch(`${API_BASE}/similar/all`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/complementary/all`).then(r => r.json()).catch(() => ({})),
            fetch(`${API_BASE}/toprated`).then(r => r.json()),
        ]);
        store.products = products;
        store.popularByCategory = popular;
        // similar/complementary come as full maps from /api/similar/all etc.
        // but our API returns per-product — load full files as fallback
        store.similarProducts = Object.keys(similar).length ? similar : await loadJSON("similar_products.json").catch(() => ({}));
        store.complementaryProducts = Object.keys(complementary).length ? complementary : await loadJSON("complementary_products.json").catch(() => ({}));
        store.topRated = topRated;
    } else {
        console.log("📁 Using static JSON files from data/");
        const [products, popular, similar, complementary, topRated] = await Promise.all([
            loadJSON("products.json"),
            loadJSON("popular_by_category.json"),
            loadJSON("similar_products.json"),
            loadJSON("complementary_products.json"),
            loadJSON("top_rated.json"),
        ]);
        store.products = products;
        store.popularByCategory = popular;
        store.similarProducts = similar;
        store.complementaryProducts = complementary;
        store.topRated = topRated;
    }
}

function productById(id) {
    return store.products.find(p => p.product_id === id);
}

// ═══════════════════════════════════════════════════════════════════════════
//  ONBOARDING
// ═══════════════════════════════════════════════════════════════════════════

function setupOnboarding() {
    const picker = document.getElementById("categoryPicker");
    const startBtn = document.getElementById("startBtn");
    const nameInput = document.getElementById("userName");
    const selected = new Set();

    // Count products per category
    const catCount = {};
    store.products.forEach(p => {
        catCount[p.category] = (catCount[p.category] || 0) + 1;
    });

    // Render category cards
    picker.innerHTML = Object.entries(CAT_META).map(([cat, m]) => `
        <div class="cat-pick-card" data-cat="${cat}">
            <span class="cat-pick-icon">${m.icon}</span>
            <div class="cat-pick-name">${esc(cat)}</div>
            <div class="cat-pick-count">${catCount[cat] || 0} products</div>
        </div>
    `).join("");

    // Toggle selection
    picker.querySelectorAll(".cat-pick-card").forEach(card => {
        card.addEventListener("click", () => {
            const cat = card.dataset.cat;
            if (selected.has(cat)) {
                selected.delete(cat);
                card.classList.remove("selected");
            } else {
                selected.add(cat);
                card.classList.add("selected");
            }
            startBtn.disabled = selected.size < 2 || nameInput.value.trim().length === 0;
        });
    });

    nameInput.addEventListener("input", () => {
        startBtn.disabled = selected.size < 2 || nameInput.value.trim().length === 0;
    });

    startBtn.addEventListener("click", () => {
        const name = nameInput.value.trim();
        if (name && selected.size >= 2) {
            const user = newUser(name, [...selected]);
            saveUser(user);
            showMainApp(user);
        }
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN APP RENDER
// ═══════════════════════════════════════════════════════════════════════════

function showMainApp(user) {
    document.getElementById("onboarding").style.display = "none";
    document.getElementById("mainApp").style.display = "block";

    // Navbar user info
    document.getElementById("userNameDisplay").textContent = user.name;
    document.getElementById("userAvatar").textContent = user.name.charAt(0).toUpperCase();
    updateCounts(user);

    renderRecommendations(user);
    renderCategorySections(user);
    setupSearch();
}

function updateCounts(user) {
    document.getElementById("cartCount").textContent = user.cart.length;
    document.getElementById("likedCount").textContent = user.liked.length;
}

// ═══════════════════════════════════════════════════════════════════════════
//  RECOMMENDATIONS SECTION
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Weighted Recommendation Engine:
 * - Uses ALL past interactions, not just the last one
 * - Recent interactions carry exponentially higher weight
 * - Each interacted product contributes similar + complementary recommendations
 * - Number of recs per product is proportional to its recency weight
 */
function renderRecommendations(user) {
    const container = document.getElementById("recsScroll");
    const subtext = document.getElementById("recSubtext");
    const MAX_RECS = 14;
    let recsProducts = [];

    if (user.interactions.length > 0) {
        const now = Date.now();
        const DECAY_HALF_LIFE_HOURS = 48; // weight halves every 48 hours

        // Group interactions by product_id — keep most recent timestamp + count
        const productWeights = {};
        user.interactions.forEach(ix => {
            const pid = ix.product_id;
            if (!productWeights[pid]) {
                productWeights[pid] = { product_id: pid, timestamp: ix.timestamp, count: 1 };
            } else {
                productWeights[pid].count++;
                if (ix.timestamp > productWeights[pid].timestamp) {
                    productWeights[pid].timestamp = ix.timestamp;
                }
            }
        });

        // Apply exponential time-decay weighting
        const weighted = Object.values(productWeights).map(pw => {
            const hoursAgo = Math.max(0, (now - pw.timestamp) / (1000 * 60 * 60));
            const decayWeight = Math.pow(0.5, hoursAgo / DECAY_HALF_LIFE_HOURS);
            return { ...pw, weight: decayWeight * (1 + Math.log2(1 + pw.count)) };
        });
        weighted.sort((a, b) => b.weight - a.weight);

        const totalWeight = weighted.reduce((s, w) => s + w.weight, 0);
        const seen = new Set();
        // Don't recommend products the user already interacted with
        weighted.forEach(pw => seen.add(pw.product_id));

        // Allocate recommendation slots proportionally to weight
        weighted.forEach(pw => {
            const slots = Math.max(1, Math.round((pw.weight / totalWeight) * MAX_RECS));
            const simSlots = Math.ceil(slots * 0.6);
            const compSlots = slots - simSlots;

            // Similar products (same sub-category)
            const simList = store.similarProducts[String(pw.product_id)] || [];
            let added = 0;
            for (const s of simList) {
                if (added >= simSlots) break;
                if (seen.has(s.product_id)) continue;
                const full = productById(s.product_id);
                if (full && user.categories.includes(full.category)) {
                    recsProducts.push(full);
                    seen.add(s.product_id);
                    added++;
                }
            }

            // Complementary / accessory products (cross-category)
            const compList = store.complementaryProducts[String(pw.product_id)] || [];
            added = 0;
            for (const c of compList) {
                if (added >= compSlots) break;
                if (seen.has(c.product_id)) continue;
                const full = productById(c.product_id);
                if (full && user.categories.includes(full.category)) {
                    recsProducts.push(full);
                    seen.add(c.product_id);
                    added++;
                }
            }
        });

        // If still short, pad with popular from user's categories
        if (recsProducts.length < 6) {
            user.categories.forEach(cat => {
                (store.popularByCategory[cat] || []).forEach(p => {
                    if (!seen.has(p.product_id) && recsProducts.length < MAX_RECS) {
                        const full = productById(p.product_id);
                        if (full) { recsProducts.push(full); seen.add(p.product_id); }
                    }
                });
            });
        }

        recsProducts = recsProducts.slice(0, MAX_RECS);

        // Build subtext showing top influencing products
        const topInfluencers = weighted.slice(0, 3).map(pw => {
            const p = productById(pw.product_id);
            return p ? p.product_name : null;
        }).filter(Boolean);

        if (topInfluencers.length > 0) {
            subtext.innerHTML = `Based on your interest in <strong>${topInfluencers.map(n => esc(n)).join('</strong>, <strong>')}</strong> & more`;
        }
    } else {
        // No interactions yet — show popular/trending from chosen categories
        user.categories.forEach(cat => {
            const popular = store.popularByCategory[cat] || [];
            recsProducts.push(...popular.slice(0, 3));
        });
        shuffleArray(recsProducts);
        recsProducts = recsProducts.slice(0, 10);
        subtext.textContent = "Trending picks from your favorite categories";
    }

    container.innerHTML = recsProducts.map(p => productCardHTML(p, true)).join("");
    attachCardEvents(container);
}

// ═══════════════════════════════════════════════════════════════════════════
//  CATEGORY SECTIONS (4 products each)
// ═══════════════════════════════════════════════════════════════════════════

function renderCategorySections(user) {
    const wrapper = document.getElementById("categorySections");
    wrapper.innerHTML = "";

    user.categories.forEach(cat => {
        const meta = CAT_META[cat] || { icon:"📦", strip:"strip-electronics", badge:"badge-electronics" };
        const catProducts = store.products.filter(p => p.category === cat);
        shuffleArray(catProducts);
        const display = catProducts.slice(0, 4);

        const section = document.createElement("section");
        section.className = "feed-section";
        section.innerHTML = `
            <div class="cat-section-header">
                <h3><span class="cat-icon">${meta.icon}</span> ${esc(cat)}</h3>
                <span class="see-all" data-cat="${cat}">See all ${catProducts.length} →</span>
            </div>
            <div class="cat-grid">
                ${display.map(p => productCardHTML(p, false)).join("")}
            </div>
        `;
        wrapper.appendChild(section);
        attachCardEvents(section);

        // "See all" expands to show all products in that category
        section.querySelector(".see-all").addEventListener("click", () => {
            const grid = section.querySelector(".cat-grid");
            grid.innerHTML = catProducts.map(p => productCardHTML(p, false)).join("");
            attachCardEvents(grid);
            section.querySelector(".see-all").style.display = "none";
        });
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  PRODUCT CARD HTML
// ═══════════════════════════════════════════════════════════════════════════

function productCardHTML(p, isRec) {
    const user = loadUser();
    const cat = p.category || "";
    const meta = CAT_META[cat] || { strip:"strip-electronics", badge:"badge-electronics" };
    const isLiked = user && user.liked.includes(p.product_id);
    const isCarted = user && user.cart.includes(p.product_id);

    return `
        <div class="product-card" data-pid="${p.product_id}">
            <div class="card-strip ${meta.strip}"></div>
            <div class="card-actions">
                <button class="card-act-btn act-like ${isLiked ? 'liked-active' : ''}"
                        data-pid="${p.product_id}" title="Wishlist">
                    ${isLiked ? '❤️' : '🤍'}
                </button>
                <button class="card-act-btn act-cart ${isCarted ? 'carted-active' : ''}"
                        data-pid="${p.product_id}" title="Add to cart">
                    ${isCarted ? '✅' : '🛒'}
                </button>
            </div>
            <div class="card-inner">
                <span class="card-cat-badge ${meta.badge}">${esc(cat)}</span>
                <div class="card-title">${esc(p.product_name)}</div>
                <div class="card-brand">${esc(p.brand || '')}${p.sub_category ? ' · '+esc(p.sub_category) : ''}</div>
                <div class="card-bottom">
                    <div class="card-price"><span class="cur">₹</span>${formatPrice(p.price)}</div>
                    <div class="card-rating">
                        <span class="stars">${renderStars(p.avg_rating)}</span>
                        <span class="r-val">${p.avg_rating}</span>
                        ${p.rating_count ? `<span class="r-cnt">(${formatCount(p.rating_count)})</span>` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
//  CARD EVENTS: click opens detail, like/cart buttons
// ═══════════════════════════════════════════════════════════════════════════

function attachCardEvents(container) {
    // Card click → open detail
    container.querySelectorAll(".product-card").forEach(card => {
        card.addEventListener("click", (e) => {
            // Don't open detail if they clicked like/cart button
            if (e.target.closest(".card-act-btn")) return;
            const pid = parseInt(card.dataset.pid, 10);
            recordInteraction(pid, "click");
            openProductDetail(pid);
        });
    });

    // Like button
    container.querySelectorAll(".act-like").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const pid = parseInt(btn.dataset.pid, 10);
            toggleLike(pid);
        });
    });

    // Cart button
    container.querySelectorAll(".act-cart").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const pid = parseInt(btn.dataset.pid, 10);
            toggleCart(pid);
        });
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  INTERACTIONS & STATE UPDATES
// ═══════════════════════════════════════════════════════════════════════════

function recordInteraction(pid, type) {
    const user = loadUser();
    if (!user) return;
    user.lastInteracted = pid;
    user.interactions.push({ product_id: pid, type, timestamp: Date.now() });
    // Keep last 50 interactions
    if (user.interactions.length > 50) user.interactions = user.interactions.slice(-50);
    saveUser(user);
    // Update the recommendation subtext live
    renderRecommendations(user);
}

function toggleLike(pid) {
    const user = loadUser();
    if (!user) return;
    const idx = user.liked.indexOf(pid);
    if (idx >= 0) {
        user.liked.splice(idx, 1);
    } else {
        user.liked.push(pid);
        user.lastInteracted = pid;
        user.interactions.push({ product_id: pid, type: "like", timestamp: Date.now() });
    }
    saveUser(user);
    updateCounts(user);
    refreshCards();
    renderRecommendations(user);
}

function toggleCart(pid) {
    const user = loadUser();
    if (!user) return;
    const idx = user.cart.indexOf(pid);
    if (idx >= 0) {
        user.cart.splice(idx, 1);
    } else {
        user.cart.push(pid);
        user.lastInteracted = pid;
        user.interactions.push({ product_id: pid, type: "add_to_cart", timestamp: Date.now() });
    }
    saveUser(user);
    updateCounts(user);
    refreshCards();
    renderRecommendations(user);
}

/** Re-render like/cart button states without full re-render */
function refreshCards() {
    const user = loadUser();
    if (!user) return;
    document.querySelectorAll(".act-like").forEach(btn => {
        const pid = parseInt(btn.dataset.pid, 10);
        const liked = user.liked.includes(pid);
        btn.innerHTML = liked ? '❤️' : '🤍';
        btn.classList.toggle("liked-active", liked);
    });
    document.querySelectorAll(".act-cart").forEach(btn => {
        const pid = parseInt(btn.dataset.pid, 10);
        const carted = user.cart.includes(pid);
        btn.innerHTML = carted ? '✅' : '🛒';
        btn.classList.toggle("carted-active", carted);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  PRODUCT DETAIL MODAL
// ═══════════════════════════════════════════════════════════════════════════

function openProductDetail(pid) {
    const p = productById(pid);
    if (!p) return;

    const user = loadUser();
    const isLiked = user && user.liked.includes(pid);
    const isCarted = user && user.cart.includes(pid);
    const cat = p.category || "";
    const meta = CAT_META[cat] || { badge: "badge-electronics", emoji: "📦" };

    // Similar products (same sub-category)
    const simList = store.similarProducts[String(pid)] || [];
    const similar = simList.map(s => {
        const full = productById(s.product_id);
        return full ? { ...full, similarity_score: s.similarity_score } : s;
    });

    // Complementary / accessory products (cross-category)
    const compList = store.complementaryProducts[String(pid)] || [];
    const accessories = compList.map(c => {
        const full = productById(c.product_id);
        return full || c;
    });

    const modal = document.getElementById("productModal");
    const body = document.getElementById("modalBody");

    body.innerHTML = `
        <div class="detail-top">
            <div class="detail-image">${meta.emoji}</div>
            <div class="detail-info">
                <span class="detail-cat ${meta.badge}">${esc(cat)}</span>
                <div class="detail-name">${esc(p.product_name)}</div>
                <div class="detail-brand">${esc(p.brand || '')}${p.sub_category ? ' · '+esc(p.sub_category) : ''}</div>
                <div class="detail-price"><span class="cur">₹</span>${formatPrice(p.price)}</div>
                <div class="detail-rating">
                    <span class="stars">${renderStars(p.avg_rating)}</span>
                    <span class="r-val">${p.avg_rating}</span>
                    ${p.rating_count ? `<span class="r-cnt">(${formatCount(p.rating_count)} ratings)</span>` : ''}
                </div>
                <div class="detail-meta">
                    ${p.price_range ? `<span class="meta-chip">${esc(p.price_range)}</span>` : ''}
                    <span class="meta-chip">Product #${p.product_id}</span>
                </div>
                <div class="detail-actions">
                    <button class="btn-action btn-cart" id="detailCartBtn" data-pid="${pid}">
                        ${isCarted ? '✅ In Cart' : '🛒 Add to Cart'}
                    </button>
                    <button class="btn-action btn-like ${isLiked ? 'active' : ''}" id="detailLikeBtn" data-pid="${pid}">
                        ${isLiked ? '❤️ Wishlisted' : '🤍 Wishlist'}
                    </button>
                </div>
            </div>
        </div>

        ${similar.length > 0 ? `
        <div class="similar-section">
            <h4>🔗 Similar Products</h4>
            <div class="similar-grid">
                ${similar.map(s => `
                    <div class="similar-card" data-pid="${s.product_id}">
                        <div class="sim-name">${esc(s.product_name)}</div>
                        <div class="sim-brand">${esc(s.brand || '')} · ${esc(s.category || '')}</div>
                        <div class="sim-bottom">
                            <span class="sim-price">₹${formatPrice(s.price)}</span>
                            <span class="sim-rating">${renderStars(s.avg_rating)} ${s.avg_rating}</span>
                        </div>
                    </div>
                `).join("")}
            </div>
        </div>` : ''}

        ${accessories.length > 0 ? `
        <div class="similar-section accessories-section">
            <h4>🎯 Accessories & Goes Well With</h4>
            <div class="similar-grid">
                ${accessories.map(a => `
                    <div class="similar-card accessory-card" data-pid="${a.product_id}">
                        <div class="sim-name">${esc(a.product_name)}</div>
                        <div class="sim-brand">${esc(a.brand || '')} · ${esc(a.category || '')}</div>
                        <div class="sim-bottom">
                            <span class="sim-price">₹${formatPrice(a.price)}</span>
                            <span class="sim-rating">${renderStars(a.avg_rating)} ${a.avg_rating}</span>
                        </div>
                    </div>
                `).join("")}
            </div>
        </div>` : ''}
    `;

    // Detail button events
    document.getElementById("detailCartBtn").addEventListener("click", () => {
        toggleCart(pid);
        const u = loadUser();
        const btn = document.getElementById("detailCartBtn");
        const inCart = u && u.cart.includes(pid);
        btn.innerHTML = inCart ? '✅ In Cart' : '🛒 Add to Cart';
    });

    document.getElementById("detailLikeBtn").addEventListener("click", () => {
        toggleLike(pid);
        const u = loadUser();
        const btn = document.getElementById("detailLikeBtn");
        const liked = u && u.liked.includes(pid);
        btn.innerHTML = liked ? '❤️ Wishlisted' : '🤍 Wishlist';
        btn.classList.toggle("active", liked);
    });

    // Similar + accessory cards open their own detail
    body.querySelectorAll(".similar-card").forEach(card => {
        card.addEventListener("click", () => {
            const spid = parseInt(card.dataset.pid, 10);
            recordInteraction(spid, "click");
            openProductDetail(spid);
        });
    });

    modal.style.display = "flex";
}

// Close modal
document.getElementById("modalClose").addEventListener("click", () => {
    document.getElementById("productModal").style.display = "none";
});
document.getElementById("productModal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.style.display = "none";
    }
});

// ═══════════════════════════════════════════════════════════════════════════
//  CART & WISHLIST SIDEBARS
// ═══════════════════════════════════════════════════════════════════════════

document.getElementById("cartBtn").addEventListener("click", () => openSidebar("cart"));
document.getElementById("likedBtn").addEventListener("click", () => openSidebar("liked"));
document.getElementById("cartClose").addEventListener("click", () => closeSidebar("cart"));
document.getElementById("likedClose").addEventListener("click", () => closeSidebar("liked"));
document.getElementById("cartSidebar").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeSidebar("cart");
});
document.getElementById("likedSidebar").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeSidebar("liked");
});

// ═══════════════════════════════════════════════════════════════════════════
//  PROFILE PANEL (edit preferences)
// ═══════════════════════════════════════════════════════════════════════════

document.getElementById("userChip").addEventListener("click", () => openProfile());
document.getElementById("profileClose").addEventListener("click", () => closeProfile());
document.getElementById("profilePanel").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeProfile();
});

function openProfile() {
    const user = loadUser();
    if (!user) return;
    const body = document.getElementById("profileBody");

    const catCount = {};
    store.products.forEach(p => { catCount[p.category] = (catCount[p.category] || 0) + 1; });

    body.innerHTML = `
        <div class="profile-section">
            <div class="profile-avatar-lg">${user.name.charAt(0).toUpperCase()}</div>
            <div class="profile-name">${esc(user.name)}</div>
            <div class="profile-stats">
                <span>🛒 ${user.cart.length} in cart</span>
                <span>❤️ ${user.liked.length} wishlisted</span>
                <span>🔄 ${user.interactions.length} interactions</span>
            </div>
        </div>
        <div class="profile-section">
            <h4>Edit Preferred Categories</h4>
            <p class="profile-hint">Select at least 2 categories. Changes are saved instantly.</p>
            <div class="profile-cat-picker">
                ${Object.entries(CAT_META).map(([cat, m]) => `
                    <div class="profile-cat-card ${user.categories.includes(cat) ? 'selected' : ''}" data-cat="${cat}">
                        <span class="cat-pick-icon">${m.icon}</span>
                        <div class="cat-pick-name">${esc(cat)}</div>
                        <div class="cat-pick-count">${catCount[cat] || 0} products</div>
                    </div>
                `).join("")}
            </div>
            <button class="btn-save-profile" id="saveProfileBtn">Save Preferences</button>
        </div>
        <div class="profile-section">
            <h4>Interaction History</h4>
            <div class="profile-history">
                ${user.interactions.length === 0 ? '<p class="empty-msg">No interactions yet</p>' :
                    [...user.interactions].reverse().slice(0, 15).map(ix => {
                        const p = productById(ix.product_id);
                        const t = new Date(ix.timestamp);
                        const timeStr = t.toLocaleDateString('en-IN', { day:'numeric', month:'short' }) + ' ' + t.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
                        return `<div class="history-item">
                            <span class="history-type">${ix.type === 'click' ? '👁️' : ix.type === 'like' ? '❤️' : '🛒'}</span>
                            <span class="history-name">${p ? esc(p.product_name) : 'Product #'+ix.product_id}</span>
                            <span class="history-time">${timeStr}</span>
                        </div>`;
                    }).join("")}
            </div>
        </div>
    `;

    // Category toggle
    const selected = new Set(user.categories);
    body.querySelectorAll(".profile-cat-card").forEach(card => {
        card.addEventListener("click", () => {
            const cat = card.dataset.cat;
            if (selected.has(cat)) { selected.delete(cat); card.classList.remove("selected"); }
            else { selected.add(cat); card.classList.add("selected"); }
        });
    });

    // Save button
    document.getElementById("saveProfileBtn").addEventListener("click", () => {
        if (selected.size < 2) {
            alert("Please select at least 2 categories.");
            return;
        }
        const u = loadUser();
        u.categories = [...selected];
        saveUser(u);
        closeProfile();
        // Re-render the feed with new categories
        renderRecommendations(u);
        renderCategorySections(u);
    });

    document.getElementById("profilePanel").style.display = "block";
}

function closeProfile() {
    document.getElementById("profilePanel").style.display = "none";
}

function openSidebar(type) {
    const user = loadUser();
    if (!user) return;
    const ids = type === "cart" ? user.cart : user.liked;
    const body = document.getElementById(type === "cart" ? "cartBody" : "likedBody");

    if (ids.length === 0) {
        body.innerHTML = `<p class="empty-msg">Your ${type === 'cart' ? 'cart' : 'wishlist'} is empty</p>`;
    } else {
        body.innerHTML = ids.map(pid => {
            const p = productById(pid);
            if (!p) return '';
            return `
                <div class="sidebar-item">
                    <div class="sidebar-item-info">
                        <div class="sidebar-item-name">${esc(p.product_name)}</div>
                        <div class="sidebar-item-meta">${esc(p.brand || '')} · ${esc(p.category || '')}</div>
                    </div>
                    <div class="sidebar-item-price">₹${formatPrice(p.price)}</div>
                    <button class="sidebar-item-remove" data-pid="${pid}" data-type="${type}">✕</button>
                </div>
            `;
        }).join("");

        // Remove buttons
        body.querySelectorAll(".sidebar-item-remove").forEach(btn => {
            btn.addEventListener("click", () => {
                const pid = parseInt(btn.dataset.pid, 10);
                if (btn.dataset.type === "cart") toggleCart(pid);
                else toggleLike(pid);
                openSidebar(type); // refresh
            });
        });
    }

    document.getElementById(type === "cart" ? "cartSidebar" : "likedSidebar").style.display = "block";
}

function closeSidebar(type) {
    document.getElementById(type === "cart" ? "cartSidebar" : "likedSidebar").style.display = "none";
}

// ═══════════════════════════════════════════════════════════════════════════
//  SEARCH
// ═══════════════════════════════════════════════════════════════════════════

function setupSearch() {
    const bar = document.getElementById("searchBar");
    let debounce;

    bar.addEventListener("input", () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            const q = bar.value.trim().toLowerCase();
            const user = loadUser();
            if (!user) return;

            if (q.length === 0) {
                // Restore normal view
                renderCategorySections(user);
                return;
            }

            // Filter products matching query within user's categories
            const results = store.products.filter(p =>
                user.categories.includes(p.category) &&
                (p.product_name.toLowerCase().includes(q) ||
                 p.brand.toLowerCase().includes(q) ||
                 p.category.toLowerCase().includes(q) ||
                 (p.sub_category && p.sub_category.toLowerCase().includes(q)))
            );

            const wrapper = document.getElementById("categorySections");
            if (results.length === 0) {
                wrapper.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-sec);">
                    No products found for "${esc(q)}"</div>`;
            } else {
                wrapper.innerHTML = `
                    <section class="feed-section">
                        <div class="cat-section-header">
                            <h3>🔍 Search results for "${esc(q)}"</h3>
                            <span class="see-all" style="cursor:default">${results.length} found</span>
                        </div>
                        <div class="cat-grid">${results.map(p => productCardHTML(p, false)).join("")}</div>
                    </section>
                `;
                attachCardEvents(wrapper);
            }
        }, 250);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  LOGOUT
// ═══════════════════════════════════════════════════════════════════════════

document.getElementById("logoutBtn").addEventListener("click", () => {
    if (confirm("Reset your profile and start over?")) {
        clearUser();
        document.getElementById("mainApp").style.display = "none";
        document.getElementById("onboarding").style.display = "flex";
        document.getElementById("userName").value = "";
        document.querySelectorAll(".cat-pick-card").forEach(c => c.classList.remove("selected"));
        document.getElementById("startBtn").disabled = true;
    }
});

// ═══════════════════════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════════════════════

function esc(str) {
    if (!str) return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

function formatPrice(price) {
    if (!price) return "0";
    return Number(price).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatCount(n) {
    if (!n) return "0";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return String(n);
}

function renderStars(rating) {
    if (!rating) return "";
    const full = Math.floor(rating);
    const half = rating - full >= 0.5 ? 1 : 0;
    const empty = 5 - full - half;
    return "★".repeat(full) + (half ? "½" : "") + "☆".repeat(empty);
}

function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

// ═══════════════════════════════════════════════════════════════════════════
//  BOOT
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
    try {
        await loadAllData();
    } catch (err) {
        console.error("Failed to load data:", err);
        document.body.innerHTML = `<div style="padding:4rem;text-align:center;color:#64748b;">
            <h2>⚠️ Data Load Error</h2>
            <p>Make sure JSON files exist in the <code>data/</code> folder.<br>
            Run <code>python backend/generate_datasets.py</code> first.</p>
        </div>`;
        return;
    }

    // Check if user already signed up (persisted)
    const existing = loadUser();
    if (existing && existing.name && existing.categories && existing.categories.length >= 2) {
        showMainApp(existing);
    } else {
        setupOnboarding();
    }
});
