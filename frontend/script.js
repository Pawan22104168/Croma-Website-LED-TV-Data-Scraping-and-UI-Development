// ============================================================
// CONFIG & STATE
// ============================================================

const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:5000/api'
    : '/api';
let currentPage = 1;
const PAGE_SIZE  = 20;

let currentFilters = {
    search:      '',
    brand:       '',
    min_price:   '',
    max_price:   '',
    screen_size: '',
    discount:    '',
    sort:        'catalog_rank'
};

// ============================================================
// DOM REFERENCES
// ============================================================

const productGrid     = document.getElementById('product-grid');
const searchInput     = document.getElementById('search-input');
const searchButton    = document.getElementById('search-button');
const searchClearBtn  = document.getElementById('search-clear');
const brandSelect     = document.getElementById('brand-select');
const sizeSelect      = document.getElementById('size-select');
const dealSelect      = document.getElementById('deal-select');
const sortSelect      = document.getElementById('sort-select');
const minPriceInput   = document.getElementById('min-price');
const maxPriceInput   = document.getElementById('max-price');
const searchStatus    = document.getElementById('search-status');
const totalStatsEl    = document.getElementById('total-stats');
const resultsInfoEl   = document.getElementById('results-info');
const paginationEl    = document.getElementById('pagination-controls');
const activeFiltersEl = document.getElementById('active-filters');
const scrollTopBtn    = document.getElementById('scroll-top-btn');

// ============================================================
// INIT — runs once on page load
// ============================================================

async function init() {
    await fetchConfig();    // screen size + deal options from DB
    await fetchBrands();    // brand dropdown from DB
    await fetchStats();     // total count + price range
    await fetchAnalytics(); // intelligence dashboard numbers
    await fetchProducts();  // product grid
    setupEventListeners();
    setupScrollTopBtn();
}

// ============================================================
// API CALLS
// ============================================================

// Loads screen size and deal filter options — generated from live DB data
async function fetchConfig() {
    try {
        const res    = await fetch(`${API_BASE_URL}/config`);
        const config = await res.json();

        if (config.screenSizes) {
            sizeSelect.innerHTML = '';
            config.screenSizes.forEach(item => {
                const opt       = document.createElement('option');
                opt.value       = item.value;
                opt.textContent = item.label;
                sizeSelect.appendChild(opt);
            });
        }

        if (config.deals) {
            dealSelect.innerHTML = '';
            config.deals.forEach(item => {
                const opt       = document.createElement('option');
                opt.value       = item.value;
                opt.textContent = item.label;
                dealSelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.error('Config load failed:', err);
    }
}

// Builds the brand dropdown from whatever brands exist in the DB
async function fetchBrands() {
    try {
        const res    = await fetch(`${API_BASE_URL}/brands`);
        const brands = await res.json();

        brandSelect.innerHTML = '<option value="">All Brands</option>';
        brands.forEach(brand => {
            const opt       = document.createElement('option');
            opt.value       = brand;
            opt.textContent = brand;
            brandSelect.appendChild(opt);
        });
    } catch (err) {
        console.error('Brands load failed:', err);
    }
}

// Loads total product count, last updated time, and price range
async function fetchStats() {
    try {
        const res   = await fetch(`${API_BASE_URL}/stats`);
        const stats = await res.json();

        totalStatsEl.textContent = `Monitoring ${stats.totalProducts} Premium Models`;

        const footerP = document.querySelector('.footer-content p');
        if (footerP && stats.lastUpdated) {
            footerP.innerHTML = `&copy; 2026 Croma LED TV Data Scraping Project &nbsp;|&nbsp; <span style="color:var(--primary)">Last Updated: ${stats.lastUpdated}</span>`;
        }

        if (stats.priceRange) {
            minPriceInput.placeholder = `From ${Math.floor(stats.priceRange.min).toLocaleString()}`;
            maxPriceInput.placeholder = `Up to ${Math.ceil(stats.priceRange.max).toLocaleString()}`;
        }
    } catch (err) {
        console.error('Stats load failed:', err);
    }
}

// Pulls aggregated market data for the top insight cards
async function fetchAnalytics() {
    try {
        const res  = await fetch(`${API_BASE_URL}/analytics`);
        const data = await res.json();

        document.getElementById('insight-top-brand').textContent = data.topBrand;
        animateCount('insight-avg-price',   0, data.avgPrice,    1400);
        animateCount('insight-max-savings', 0, data.maxSavings,  1400);
        animateCount('insight-avg-savings', 0, data.avgDiscount, 1400);
    } catch (err) {
        console.error('Analytics load failed:', err);
    }
}

// Main fetch — called whenever a filter, sort, or page changes
async function fetchProducts() {
    productGrid.innerHTML = '';
    renderSkeletons();

    const params = new URLSearchParams({
        page:        currentPage,
        limit:       PAGE_SIZE,
        search:      currentFilters.search,
        brand:       currentFilters.brand,
        screen_size: currentFilters.screen_size,
        discount:    currentFilters.discount,
        sort:        currentFilters.sort,
        min_price:   currentFilters.min_price,
        max_price:   currentFilters.max_price
    });

    try {
        const res        = await fetch(`${API_BASE_URL}/products?${params}`);
        const data       = await res.json();
        const products   = data.products;
        const searchInfo = data.searchInfo;

        // Show the right banner based on what the search returned
        if (searchInfo && searchInfo.searchActive) {
            if (products.length === 0) {
                searchStatus.innerHTML = `
                    <div class="alert alert-warning">
                        <strong>Not Found:</strong> No results for "${currentFilters.search}".
                        Try a broader search or remove some filters.
                    </div>`;
            } else if (!searchInfo.isExactMatch) {
                searchStatus.innerHTML = `
                    <div class="alert alert-info">
                        <strong>Relevant Selections:</strong> Exact model not found.
                        Showing the most relevant matches.
                    </div>`;
            } else {
                searchStatus.innerHTML = `
                    <div class="alert alert-success">
                        <strong>High-Precision Match:</strong>
                        Results optimized for "${currentFilters.search}".
                    </div>`;
            }
        } else {
            searchStatus.innerHTML = '';
        }

        if (products.length === 0) {
            productGrid.innerHTML = `
                <div class="loader">
                    <div style="font-size:2.5rem;margin-bottom:1rem">&#128219;</div>
                    <h3 style="color:var(--text);margin-bottom:.5rem">No Products Found</h3>
                    <p style="color:var(--muted)">Try adjusting your filters or broadening your search.</p>
                </div>`;
        } else {
            renderProducts(products);
            setupGlowEffects();
        }

        resultsInfoEl.textContent = `Found ${data.pagination.totalResults.toLocaleString()} matching results`;
        renderFilterPills();
        renderPagination(data.pagination);

    } catch (err) {
        console.error('Products load failed:', err);
        productGrid.innerHTML = `
            <div class="loader" style="color:var(--red)">
                Could not connect to the API. Make sure Flask is running on port 5000.
            </div>`;
    }
}

// ============================================================
// RENDER HELPERS
// ============================================================

// Injects product cards with a small stagger delay each so they wave in
function renderProducts(products) {
    productGrid.innerHTML = products.map((product, index) => {
        const discount = product.discountValue || '';
        const rating   = product.averageRating || 0;
        const img      = product.plpImage.replace(/ /g, '%20');
        const delay    = (index * 0.055).toFixed(2);
        const url      = `https://www.croma.com${product.url}`;

        return `
        <div class="product-card" style="animation-delay:${delay}s">
            <div class="card-glow"></div>
            <div class="product-image-container">
                <a href="${url}" target="_blank" rel="noopener">
                    <img src="${img}" alt="${product.name}" loading="lazy">
                </a>
                ${discount ? `<div class="discount-badge">${discount}</div>` : ''}
            </div>
            <div class="product-info">
                <div class="product-brand">${product.brand}</div>
                <div class="product-name" title="${product.name}">
                    <a href="${url}" target="_blank" rel="noopener">${product.name}</a>
                </div>
                <div class="product-rating">
                    <span class="star">&#9733;</span>
                    <span>${rating}</span>
                    <span style="color:var(--muted)">(${product.numberOfRatings || 0})</span>
                </div>
                <div class="price-container">
                    <span class="current-price">${product.price.formattedValue}</span>
                    ${product.mrp && product.mrp.value > product.price.value
                        ? `<span class="original-price">${product.mrp.formattedValue}</span>`
                        : ''}
                </div>
                <a href="${url}" target="_blank" rel="noopener" class="view-link">View on Croma &#8594;</a>
            </div>
        </div>`;
    }).join('');
}

// Show 8 pulsing placeholder cards while real data is loading
function renderSkeletons() {
    let html = '';
    for (let i = 0; i < 8; i++) {
        html += `
        <div class="skeleton-card">
            <div class="skeleton-pulse"></div>
            <div class="skeleton-img"></div>
            <div class="skeleton-text"></div>
            <div class="skeleton-text" style="width:60%"></div>
            <div class="skeleton-price"></div>
        </div>`;
    }
    productGrid.innerHTML = `<div class="loader-container">${html}</div>`;
}

// Build the row of active filter pills above the product grid
function renderFilterPills() {
    activeFiltersEl.innerHTML = '';

    const pills = [];

    if (currentFilters.search)
        pills.push({ label: `"${currentFilters.search}"`, key: 'search' });

    if (currentFilters.brand)
        pills.push({ label: currentFilters.brand, key: 'brand' });

    if (currentFilters.screen_size)
        pills.push({ label: `${currentFilters.screen_size} inch`, key: 'screen_size' });

    if (currentFilters.discount)
        pills.push({ label: `${currentFilters.discount}%+ Off`, key: 'discount' });

    if (currentFilters.min_price || currentFilters.max_price) {
        const from  = currentFilters.min_price ? `&#8377;${Number(currentFilters.min_price).toLocaleString()}` : '';
        const to    = currentFilters.max_price ? `&#8377;${Number(currentFilters.max_price).toLocaleString()}` : '';
        const label = from && to ? `${from} &#8211; ${to}` : from || `Up to ${to}`;
        pills.push({ label, key: 'price' });
    }

    if (pills.length === 0) return;

    pills.forEach(pill => {
        const div       = document.createElement('div');
        div.className   = 'filter-pill';
        div.innerHTML   = `${pill.label} <button onclick="removePill('${pill.key}')" title="Remove">&#x2715;</button>`;
        activeFiltersEl.appendChild(div);
    });

    const clearBtn       = document.createElement('button');
    clearBtn.className   = 'clear-all-btn';
    clearBtn.textContent = 'Clear All';
    clearBtn.onclick     = clearAllFilters;
    activeFiltersEl.appendChild(clearBtn);
}

// Prev / Next + numbered page buttons
function renderPagination(pagination) {
    const { totalPages, currentPage: active } = pagination;
    paginationEl.innerHTML = '';
    if (totalPages <= 1) return;

    const prevBtn       = document.createElement('button');
    prevBtn.className   = 'page-btn';
    prevBtn.textContent = '←';
    prevBtn.disabled    = active === 1;
    prevBtn.onclick     = () => { currentPage--; fetchProducts(); scrollToTop(); };
    paginationEl.appendChild(prevBtn);

    let start = Math.max(1, active - 2);
    let end   = Math.min(totalPages, start + 4);
    if (end - start < 4) start = Math.max(1, end - 4);

    for (let i = start; i <= end; i++) {
        const btn      = document.createElement('button');
        btn.className  = `page-btn ${i === active ? 'active' : ''}`;
        btn.textContent = i;
        btn.onclick    = () => { currentPage = i; fetchProducts(); scrollToTop(); };
        paginationEl.appendChild(btn);
    }

    const nextBtn       = document.createElement('button');
    nextBtn.className   = 'page-btn';
    nextBtn.textContent = '→';
    nextBtn.disabled    = active === totalPages;
    nextBtn.onclick     = () => { currentPage++; fetchProducts(); scrollToTop(); };
    paginationEl.appendChild(nextBtn);

    // Add a subtle "Back to top" text link after the page buttons
    const topLink       = document.createElement('a');
    topLink.className   = 'back-to-top-link';
    topLink.textContent = '↑ Back to top';
    topLink.onclick     = scrollToTop;
    paginationEl.appendChild(topLink);
}

// ============================================================
// FILTER HELPERS
// ============================================================

// Remove one filter by key and refresh
function removePill(key) {
    if (key === 'search') {
        currentFilters.search = '';
        searchInput.value     = '';
        searchClearBtn.style.display = 'none';
    } else if (key === 'brand') {
        currentFilters.brand = '';
        brandSelect.value    = '';
    } else if (key === 'screen_size') {
        currentFilters.screen_size = '';
        sizeSelect.value           = '';
    } else if (key === 'discount') {
        currentFilters.discount = '';
        dealSelect.value        = '';
    } else if (key === 'price') {
        currentFilters.min_price = '';
        currentFilters.max_price = '';
        minPriceInput.value      = '';
        maxPriceInput.value      = '';
    }
    currentPage = 1;
    fetchProducts();
}

// Reset everything back to the default state
function clearAllFilters() {
    currentFilters = {
        search: '', brand: '', min_price: '', max_price: '',
        screen_size: '', discount: '', sort: currentFilters.sort
    };
    searchInput.value           = '';
    brandSelect.value           = '';
    sizeSelect.value            = '';
    dealSelect.value            = '';
    minPriceInput.value         = '';
    maxPriceInput.value         = '';
    searchClearBtn.style.display = 'none';
    currentPage = 1;
    fetchProducts();
}

// ============================================================
// EVENT LISTENERS
// ============================================================

function setupEventListeners() {

    searchButton.onclick = () => {
        // If the user typed something, drop the brand filter to avoid conflicts
        if (searchInput.value.trim()) {
            brandSelect.value    = '';
            currentFilters.brand = '';
        }
        currentFilters.search = searchInput.value.trim();
        currentPage = 1;
        fetchProducts();
    };

    searchInput.onkeypress = (e) => {
        if (e.key === 'Enter') searchButton.onclick();
    };

    // Show/hide the ✕ clear button as the user types
    searchInput.oninput = () => {
        searchClearBtn.style.display = searchInput.value ? 'block' : 'none';
    };

    searchClearBtn.onclick = () => {
        searchInput.value            = '';
        currentFilters.search        = '';
        searchClearBtn.style.display = 'none';
        currentPage = 1;
        fetchProducts();
    };

    // Selecting a brand clears the text search to prevent brand conflicts
    brandSelect.onchange = (e) => {
        if (e.target.value) {
            searchInput.value            = '';
            currentFilters.search        = '';
            searchClearBtn.style.display = 'none';
        }
        currentFilters.brand = e.target.value;
        currentPage = 1;
        fetchProducts();
    };

    // Size, deals, and sort don't need to clear the search
    sizeSelect.onchange = (e) => { currentFilters.screen_size = e.target.value; currentPage = 1; fetchProducts(); };
    dealSelect.onchange = (e) => { currentFilters.discount    = e.target.value; currentPage = 1; fetchProducts(); };
    sortSelect.onchange = (e) => { currentFilters.sort        = e.target.value; currentPage = 1; fetchProducts(); };

    // Debounced price filter so we don't hit the API on every keystroke
    const handlePrice = () => {
        const min = parseFloat(minPriceInput.value);
        const max = parseFloat(maxPriceInput.value);

        if (!isNaN(min) && !isNaN(max) && min > max) {
            productGrid.innerHTML = `
                <div class="loader">
                    <div style="font-size:2rem;margin-bottom:.75rem">&#9888;&#65039;</div>
                    <h3 style="color:var(--red);margin-bottom:.5rem">Invalid Price Range</h3>
                    <p style="color:var(--muted)">Min price cannot be higher than Max price.</p>
                </div>`;
            paginationEl.innerHTML = '';
            return;
        }

        currentFilters.min_price = minPriceInput.value;
        currentFilters.max_price = maxPriceInput.value;

        clearTimeout(window._priceTimer);
        window._priceTimer = setTimeout(() => { currentPage = 1; fetchProducts(); }, 600);
    };

    minPriceInput.oninput = handlePrice;
    maxPriceInput.oninput = handlePrice;

    // Press "/" anywhere on the page to jump focus to the search bar
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

// ============================================================
// SCROLL TO TOP
// ============================================================

function setupScrollTopBtn() {
    window.addEventListener('scroll', () => {
        scrollTopBtn.classList.toggle('visible', window.scrollY > 320);
    });
    scrollTopBtn.onclick = scrollToTop;
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================================
// VISUAL EFFECTS
// ============================================================

// Tracks mouse position per card so the radial glow follows the cursor
function setupGlowEffects() {
    document.querySelectorAll('.bento-card, .product-card').forEach(card => {
        card.onmousemove = (e) => {
            const r = card.getBoundingClientRect();
            card.style.setProperty('--mouse-x', `${e.clientX - r.left}px`);
            card.style.setProperty('--mouse-y', `${e.clientY - r.top}px`);
        };
    });
}

// Counts a number up from 0 to end over `duration` ms
function animateCount(id, start, end, duration) {
    const el = document.getElementById(id);
    if (!el) return;

    let ts = null;
    const step = (now) => {
        if (!ts) ts = now;
        const progress = Math.min((now - ts) / duration, 1);
        el.textContent = Math.floor(progress * (end - start) + start).toLocaleString();
        if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

// ============================================================
// START
// ============================================================

init();
