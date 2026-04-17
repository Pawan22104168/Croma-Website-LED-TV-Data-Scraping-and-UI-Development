// Configuration
const API_BASE_URL = 'http://localhost:5000/api';
let currentPage = 1;
const limit = 20;

// State Management
let currentFilters = {
    search: '',
    brand: '',
    min_price: '',
    max_price: '',
    screen_size: '',
    discount: '',
    sort: 'catalog_rank'
};

// DOM Elements
const productGrid = document.getElementById('product-grid');
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const brandSelect = document.getElementById('brand-select');
const sizeSelect = document.getElementById('size-select');
const dealSelect = document.getElementById('deal-select');
const sortSelect = document.getElementById('sort-select');
const minPriceInput = document.getElementById('min-price');
const maxPriceInput = document.getElementById('max-price');
const searchStatus = document.getElementById('search-status');
const totalStatsContainer = document.getElementById('total-stats');
const resultsInfoContainer = document.getElementById('results-info');
const paginationControls = document.getElementById('pagination-controls');

/**
 * Initialize application
 */
async function init() {
    console.log('Frontend Initializing...');
    await fetchConfig(); // Load dynamic UI configuration
    await fetchBrands();
    await fetchStats();
    await fetchProducts();
    setupEventListeners();
}

/**
 * Fetch dynamic UI configuration settings from the API
 */
async function fetchConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/config`);
        const config = await response.json();
        
        // Populate Screen Size
        if (config.screenSizes) {
            sizeSelect.innerHTML = '';
            config.screenSizes.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.value;
                opt.textContent = item.label;
                sizeSelect.appendChild(opt);
            });
        }
        
        // Populate Deals
        if (config.deals) {
            dealSelect.innerHTML = '';
            config.deals.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.value;
                opt.textContent = item.label;
                dealSelect.appendChild(opt);
            });
        }
    } catch (error) {
        console.error('Error fetching config:', error);
    }
}

/**
 * Fetch products from the Flask API
 */
async function fetchProducts() {
    productGrid.innerHTML = '<div class="loader">Querying MongoDB...</div>';
    
    // Build query string
    const params = new URLSearchParams({
        page: currentPage,
        limit: limit,
        search: currentFilters.search,
        brand: currentFilters.brand,
        screen_size: currentFilters.screen_size,
        discount: currentFilters.discount,
        sort: currentFilters.sort,
        min_price: currentFilters.min_price,
        max_price: currentFilters.max_price
    });

    try {
        const response = await fetch(`${API_BASE_URL}/products?${params}`);
        const data = await response.json();
        const products = data.products;
        const searchInfo = data.searchInfo;

        // --- Handle Intelligent Search Feedback ---
        if (searchInfo && searchInfo.searchActive) {
            if (products.length === 0) {
                searchStatus.innerHTML = `
                    <div class="alert alert-warning">
                        <strong>Product Not Found:</strong> We couldn't find an exact match for "${currentFilters.search}".
                        <br>Searching for similar products...
                    </div>`;
                // If zero results, try clear broad search automatically 
                // (or just let the user see the zero results state)
            } else if (!searchInfo.isExactMatch) {
                searchStatus.innerHTML = `
                    <div class="alert alert-info">
                        <strong>Relevant Selections:</strong> Exact model not found. Showing the most relevant matches for your query.
                    </div>`;
            } else {
                searchStatus.innerHTML = `
                    <div class="alert alert-success">
                        <strong>High-Precision Match:</strong> Results optimized for "${currentFilters.search}".
                    </div>`;
            }
        } else {
            searchStatus.innerHTML = ''; // Clear if no search
        }

        if (products.length === 0) {
            productGrid.innerHTML = `
                <div class="loader" style="padding-top: 5rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">😢</div>
                    <h3 style="color: var(--text-main); margin-bottom: 0.5rem;">No Products Available</h3>
                    <p style="color: var(--text-muted);">We couldn't find any TVs matching this specific price range or brand.</p>
                    <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem;">Try clearing filters or broadening your budget.</p>
                </div>
            `;
        } else {
            renderProducts(products);
        }
        
        // Update results info text
        const totalFound = data.pagination.totalResults;
        resultsInfoContainer.textContent = `Found ${totalFound} matching results for your selection`;
        
        renderPagination(data.pagination);
    } catch (error) {
        console.error('Error fetching products:', error);
        productGrid.innerHTML = '<div class="loader" style="color: #ff4757">Error: Could not connect to the Backend API. Make sure Flask is running!</div>';
    }
}

/**
 * Render product cards into the grid
 */
function renderProducts(products) {
    if (products.length === 0) {
        productGrid.innerHTML = `
            <div class="loader" style="padding-top: 5rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">😢</div>
                <h3 style="color: var(--text-main); margin-bottom: 0.5rem;">No Products Available</h3>
                <p style="color: var(--text-muted);">We couldn't find any TVs matching this specific price range or brand.</p>
                <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem;">Try clearing filters or broadening your budget.</p>
            </div>
        `;
        return;
    }

    productGrid.innerHTML = products.map(product => {
        const discountValue = product.discountValue || '';
        const rating = product.averageRating || 0;
        
        // Handle images that might have spaces in URLs (common in Croma data)
        const imgSrc = product.plpImage.replace(/ /g, '%20');
        
        return `
            <div class="product-card">
                <div class="product-image-container">
                    <a href="https://www.croma.com${product.url}" target="_blank">
                        <img src="${imgSrc}" alt="${product.name}" loading="lazy">
                    </a>
                    ${discountValue ? `<div class="discount-badge">${discountValue}</div>` : ''}
                </div>
                <div class="product-info">
                    <div class="product-brand">${product.brand}</div>
                    <div class="product-name" title="${product.name}">
                        <a href="https://www.croma.com${product.url}" target="_blank" style="text-decoration: none; color: inherit;">
                            ${product.name}
                        </a>
                    </div>
                    <div class="product-rating">
                        <span class="star">★</span>
                        <span>${rating}</span>
                        <span style="color: #8b949e">(${product.numberOfRatings || 0})</span>
                    </div>
                    <div class="price-container">
                        <span class="current-price">${product.price.formattedValue}</span>
                        ${product.mrp && product.mrp.value > product.price.value ? 
                            `<span class="original-price">${product.mrp.formattedValue}</span>` : ''}
                    </div>
                    <a href="https://www.croma.com${product.url}" target="_blank" class="view-link">View on Croma →</a>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Fetch and populate brand dropdown
 */
async function fetchBrands() {
    try {
        const response = await fetch(`${API_BASE_URL}/brands`);
        const brands = await response.json();
        
        brandSelect.innerHTML = '<option value="">All Brands</option>';
        brands.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            brandSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching brands:', error);
    }
}

/**
 * Fetch stats for the header and placeholders
 */
async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        const stats = await response.json();
        totalStatsContainer.textContent = `Monitoring ${stats.totalProducts} Premium Models`;
        
        // Update Footer with Data Freshness Timestamp
        const footerText = document.querySelector('.footer-content p');
        if (footerText && stats.lastUpdated) {
            footerText.innerHTML = `&copy; 2026 Croma LED TV Data Scraping Project | <span style="color: var(--primary-color)">Last Updated: ${stats.lastUpdated}</span>`;
        }
        
        // Inject database min/max into placeholders
        if (stats.priceRange) {
            minPriceInput.placeholder = `From ${Math.floor(stats.priceRange.min).toLocaleString()}`;
            maxPriceInput.placeholder = `Up to ${Math.ceil(stats.priceRange.max).toLocaleString()}`;
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

/**
 * Render pagination buttons
 */
function renderPagination(pagination) {
    const { totalPages, currentPage: activePage } = pagination;
    paginationControls.innerHTML = '';

    if (totalPages <= 1) return;

    // Previous Button
    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn';
    prevBtn.textContent = '←';
    prevBtn.disabled = activePage === 1;
    prevBtn.onclick = () => { currentPage--; fetchProducts(); window.scrollTo({top: 0, behavior: 'smooth'}); };
    paginationControls.appendChild(prevBtn);

    // Page Numbers (limited to 5 for brevity)
    let start = Math.max(1, activePage - 2);
    let end = Math.min(totalPages, start + 4);
    if (end - start < 4) start = Math.max(1, end - 4);

    for (let i = start; i <= end; i++) {
        const btn = document.createElement('button');
        btn.className = `page-btn ${i === activePage ? 'active' : ''}`;
        btn.textContent = i;
        btn.onclick = () => { currentPage = i; fetchProducts(); window.scrollTo({top: 0, behavior: 'smooth'}); };
        paginationControls.appendChild(btn);
    }

    // Next Button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn';
    nextBtn.textContent = '→';
    nextBtn.disabled = activePage === totalPages;
    nextBtn.onclick = () => { currentPage++; fetchProducts(); window.scrollTo({top: 0, behavior: 'smooth'}); };
    paginationControls.appendChild(nextBtn);
}

/**
 * Set up event listeners for filters
 */
function setupEventListeners() {
    // Search Button
    searchButton.onclick = () => {
        if (searchInput.value.trim() !== "") {
            brandSelect.value = "";
            currentFilters.brand = "";
        }
        currentFilters.search = searchInput.value;
        currentPage = 1;
        fetchProducts();
    };

    // Enter Key on Search
    searchInput.onkeypress = (e) => {
        if (e.key === 'Enter') {
            if (searchInput.value.trim() !== "") {
                brandSelect.value = "";
                currentFilters.brand = "";
            }
            currentFilters.search = searchInput.value;
            currentPage = 1;
            fetchProducts();
        }
    };

    // Brand Changes
    brandSelect.onchange = (e) => {
        if (e.target.value !== "") {
            searchInput.value = "";
            currentFilters.search = "";
        }
        currentFilters.brand = e.target.value;
        currentPage = 1;
        fetchProducts();
    };

    // Screen Size Changes
    sizeSelect.onchange = (e) => {
        currentFilters.screen_size = e.target.value;
        currentPage = 1;
        fetchProducts();
    };

    // Deal Finder Changes
    dealSelect.onchange = (e) => {
        currentFilters.discount = e.target.value;
        currentPage = 1;
        fetchProducts();
    };

    sortSelect.onchange = (e) => {
        currentFilters.sort = e.target.value;
        currentPage = 1;
        fetchProducts();
    };

    // Manual Price Inputs with Debouncing
    const handlePriceChange = () => {
        const minVal = parseFloat(minPriceInput.value);
        const maxVal = parseFloat(maxPriceInput.value);

        // Validation: Safety Lock
        if (!isNaN(minVal) && !isNaN(maxVal) && minVal > maxVal) {
            productGrid.innerHTML = `
                <div class="loader" style="padding-top: 5rem;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                    <h3 style="color: var(--accent-red); margin-bottom: 0.5rem;">Invalid Price Range</h3>
                    <p style="color: var(--text-muted);">Your <strong>Min price</strong> cannot be higher than your <strong>Max price</strong>.</p>
                    <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem;">Please adjust your budget to see matching TVs.</p>
                </div>
            `;
            paginationControls.innerHTML = '';
            return; // Skip API call
        }

        currentFilters.min_price = minPriceInput.value;
        currentFilters.max_price = maxPriceInput.value;
        
        clearTimeout(window.priceTimeout);
        window.priceTimeout = setTimeout(() => {
            currentPage = 1;
            fetchProducts();
        }, 600);
    };

    minPriceInput.oninput = handlePriceChange;
    maxPriceInput.oninput = handlePriceChange;
}

// Start the APP
init();
