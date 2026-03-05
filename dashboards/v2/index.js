/**
 * ImmoLux Dashboard - v2.0.0-beta
 * Main Application Logic
 * Date: 2026-03-05
 *
 * Features:
 * - Sortable & filterable table with localStorage persistence
 * - Multiple views: by city, by price, map
 * - CSV export with current filters
 * - Web Share API integration
 * - URL state management (query params)
 * - Accessible markup and ARIA labels
 */

'use strict';

// ==================== CONFIGURATION ====================
const CONFIG = {
    SITE_COLORS: window.SITE_COLORS || {},
    DEFAULT_SORT_COL: 'price',
    DEFAULT_SORT_ASC: true,
    MAP_INIT_LAT: 49.6116,
    MAP_INIT_LON: 6.1319,
    MAP_INIT_ZOOM: 10,
};

// ==================== STATE ====================
const state = {
    sortCol: localStorage.getItem('sortCol') || CONFIG.DEFAULT_SORT_COL,
    sortAsc: localStorage.getItem('sortAsc') !== 'false',
    filtered: [],
    mapInitialized: false,
};

// ==================== UTILITY FUNCTIONS ====================

/**
 * Format number with thousand separators
 */
function formatNumber(n) {
    return n ? n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : '—';
}

/**
 * Create site badge HTML
 */
function createSiteBadge(site) {
    const bg = CONFIG.SITE_COLORS[site] || '#888';
    return `<span class="site-badge" style="background:${bg}">${site}</span>`;
}

/**
 * Sanitize URL parameters
 */
function sanitizeUrlParam(param) {
    return encodeURIComponent(param).replace(/%20/g, '+');
}

/**
 * Get current filter state as URL params
 */
function getFilterStateAsUrl() {
    const city = document.getElementById('f-city')?.value || '';
    const pmin = document.getElementById('f-pmin')?.value || '';
    const pmax = document.getElementById('f-pmax')?.value || '';
    const site = document.getElementById('f-site')?.value || '';
    const smin = document.getElementById('f-smin')?.value || '';

    const params = new URLSearchParams();
    if (city) params.set('city', city);
    if (pmin) params.set('pmin', pmin);
    if (pmax) params.set('pmax', pmax);
    if (site) params.set('site', site);
    if (smin) params.set('smin', smin);
    params.set('sort', `${state.sortCol}:${state.sortAsc ? 'asc' : 'desc'}`);

    return params.toString();
}

/**
 * Restore filter state from URL params
 */
function restoreFilterStateFromUrl() {
    const params = new URLSearchParams(window.location.search);

    if (params.has('city')) document.getElementById('f-city').value = params.get('city');
    if (params.has('pmin')) document.getElementById('f-pmin').value = params.get('pmin');
    if (params.has('pmax')) document.getElementById('f-pmax').value = params.get('pmax');
    if (params.has('site')) document.getElementById('f-site').value = params.get('site');
    if (params.has('smin')) document.getElementById('f-smin').value = params.get('smin');

    if (params.has('sort')) {
        const [col, dir] = params.get('sort').split(':');
        state.sortCol = col;
        state.sortAsc = dir === 'asc';
    }
}

/**
 * Update URL with current filter state
 */
function updateUrlState() {
    const url = new URL(window.location);
    url.search = getFilterStateAsUrl();
    window.history.replaceState(null, '', url);
}

// ==================== TABLE FILTERING & SORTING ====================

function applyFilters() {
    try {
        const city = document.getElementById('f-city').value;
        const pmin = parseInt(document.getElementById('f-pmin').value) || 0;
        const pmax = parseInt(document.getElementById('f-pmax').value) || 999999;
        const site = document.getElementById('f-site').value;
        const smin = parseInt(document.getElementById('f-smin').value) || 0;

        state.filtered = window.LISTINGS.filter(l => {
            if (city && l.city !== city) return false;
            if (l.price < pmin || l.price > pmax) return false;
            if (site && l.site !== site) return false;
            if (smin && (!l.surface || l.surface < smin)) return false;
            return true;
        });

        sortAndRender();
        updateUrlState();
    } catch (err) {
        console.error('Error applying filters:', err);
    }
}

function sortAndRender() {
    try {
        state.filtered.sort((a, b) => {
            let va = a[state.sortCol];
            let vb = b[state.sortCol];

            if (va == null) va = state.sortAsc ? Infinity : -Infinity;
            if (vb == null) vb = state.sortAsc ? Infinity : -Infinity;

            if (typeof va === 'string') {
                return state.sortAsc
                    ? va.localeCompare(vb, 'fr-FR')
                    : vb.localeCompare(va, 'fr-FR');
            }
            return state.sortAsc ? va - vb : vb - va;
        });

        renderTable();
    } catch (err) {
        console.error('Error sorting:', err);
    }
}

function renderTable() {
    try {
        const tbody = document.getElementById('table-body');
        const count = document.getElementById('table-count');

        count.textContent = `${state.filtered.length} / ${window.LISTINGS.length}`;
        count.setAttribute('aria-live', 'polite');

        if (!state.filtered.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">Aucune annonce</td></tr>';
            return;
        }

        tbody.innerHTML = state.filtered.map(l => {
            const priceColor = l.price_m2
                ? (l.price_m2 < 20 ? '#28a745' : l.price_m2 > 30 ? '#dc3545' : '#ffc107')
                : '#999';

            return `
                <tr>
                    <td>${createSiteBadge(l.site)}</td>
                    <td>${l.city || '—'}</td>
                    <td><strong>${formatNumber(l.price)}€</strong></td>
                    <td>${l.rooms || '—'}</td>
                    <td>${l.surface || '—'}</td>
                    <td><span style="color:${priceColor}">${l.price_m2 ? l.price_m2 + '€' : '—'}</span></td>
                    <td>${l.distance_km != null ? l.distance_km + ' km' : '—'}</td>
                    <td>
                        <a href="${l.url}" target="_blank" rel="noopener noreferrer">${(l.title || 'Voir').substring(0, 40)}</a>
                        <a href="https://wa.me/?text=${encodeURIComponent(l.city + ' ' + l.price + '€ - ' + l.url)}" target="_blank" rel="noopener noreferrer" title="Partager sur WhatsApp" aria-label="Partager sur WhatsApp">📱</a>
                        <a href="https://t.me/share/url?url=${encodeURIComponent(l.url)}&text=${encodeURIComponent(l.city + ' ' + l.price + '€')}" target="_blank" rel="noopener noreferrer" title="Partager sur Telegram" aria-label="Partager sur Telegram">✈️</a>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Error rendering table:', err);
    }
}

function resetFilters() {
    ['f-city', 'f-pmin', 'f-pmax', 'f-site', 'f-smin'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    applyFilters();
}

// ==================== TABLE HEADER SORTING ====================

function initTableSorting() {
    document.querySelectorAll('#main-table th[data-col]').forEach(th => {
        th.style.cursor = 'pointer';
        th.setAttribute('tabindex', '0');

        th.addEventListener('click', () => handleSort(th));
        th.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSort(th);
            }
        });
    });

    updateSortArrows();
}

function handleSort(th) {
    const col = th.dataset.col;

    if (state.sortCol === col) {
        state.sortAsc = !state.sortAsc;
    } else {
        state.sortCol = col;
        state.sortAsc = true;
    }

    localStorage.setItem('sortCol', state.sortCol);
    localStorage.setItem('sortAsc', state.sortAsc);

    updateSortArrows();
    sortAndRender();
}

function updateSortArrows() {
    document.querySelectorAll('#main-table .sort-arrow').forEach(arrow => {
        arrow.classList.remove('active');
        arrow.innerHTML = '▲';
    });

    const activeHeader = document.querySelector(`#main-table th[data-col="${state.sortCol}"]`);
    if (activeHeader) {
        const arrow = activeHeader.querySelector('.sort-arrow');
        if (arrow) {
            arrow.classList.add('active');
            arrow.innerHTML = state.sortAsc ? '▲' : '▼';
        }
    }
}

// ==================== FILTER INITIALIZATION ====================

function initFilters() {
    try {
        // Get unique cities (normalized)
        const cities = typeof CityNormalizer !== 'undefined' && CityNormalizer.getUniqueCities
            ? CityNormalizer.getUniqueCities(window.LISTINGS)
            : [...new Set(window.LISTINGS
                .map(l => l.city)
                .filter(c => c && c !== 'N/A')
            )].sort((a, b) => a.localeCompare(b, 'fr-FR'));

        const sites = [...new Set(window.LISTINGS
            .map(l => l.site)
            .filter(Boolean)
        )].sort();

        // Populate city select
        const citySelect = document.getElementById('f-city');
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        });

        // Populate site select
        const siteSelect = document.getElementById('f-site');
        sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site;
            option.textContent = site;
            siteSelect.appendChild(option);
        });

        // Populate site badges
        const badgesDiv = document.getElementById('siteBadges');
        const siteCounts = {};
        window.LISTINGS.forEach(l => {
            siteCounts[l.site] = (siteCounts[l.site] || 0) + 1;
        });

        badgesDiv.innerHTML = Object.entries(siteCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([site, count]) => {
                const bg = CONFIG.SITE_COLORS[site] || '#888';
                return `<span class="site-badge" style="background:${bg}">${site} (${count})</span>`;
            })
            .join(' ');
    } catch (err) {
        console.error('Error initializing filters:', err);
    }
}

// ==================== CITY VIEW ====================

function renderCityView() {
    try {
        const container = document.getElementById('city-container');
        const groups = {};

        window.LISTINGS.forEach(l => {
            const city = l.city || 'N/A';
            if (!groups[city]) groups[city] = [];
            groups[city].push(l);
        });

        const sorted = Object.entries(groups).sort((a, b) => b[1].length - a[1].length);

        container.innerHTML = sorted.map(([city, items]) => {
            const prices = items.filter(l => l.price > 0).map(l => l.price);
            const avg = prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0;
            const min = prices.length ? Math.min(...prices) : 0;
            const max = prices.length ? Math.max(...prices) : 0;

            const rows = items
                .sort((a, b) => (a.price || 0) - (b.price || 0))
                .map(l => `
                    <tr>
                        <td>${createSiteBadge(l.site)}</td>
                        <td><strong>${formatNumber(l.price)}€</strong></td>
                        <td>${l.rooms || '—'} ch.</td>
                        <td>${l.surface || '—'} m²</td>
                        <td>${l.price_m2 ? l.price_m2 + ' €/m²' : '—'}</td>
                        <td><a href="${l.url}" target="_blank" rel="noopener noreferrer">${(l.title || 'Voir').substring(0, 45)}</a></td>
                    </tr>
                `)
                .join('');

            return `
                <div class="city-group">
                    <h5>📍 ${city} <span class="listing-count">(${items.length} ann. | moy. ${formatNumber(avg)}€ | ${formatNumber(min)}€ - ${formatNumber(max)}€)</span></h5>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <caption class="visually-hidden">Annonces à ${city}</caption>
                            <thead>
                                <tr>
                                    <th scope="col">Site</th>
                                    <th scope="col">Prix</th>
                                    <th scope="col">Ch.</th>
                                    <th scope="col">m²</th>
                                    <th scope="col">€/m²</th>
                                    <th scope="col">Titre</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error rendering city view:', err);
    }
}

// ==================== PRICE VIEW ====================

function renderPriceView() {
    try {
        const container = document.getElementById('price-container');
        const ranges = [
            { label: 'Moins de 1 500 €', min: 0, max: 1499, color: '#2ECC71' },
            { label: '1 500 - 2 000 €', min: 1500, max: 1999, color: '#36A2EB' },
            { label: '2 000 - 2 500 €', min: 2000, max: 2499, color: '#FFCE56' },
            { label: 'Plus de 2 500 €', min: 2500, max: 999999, color: '#FF6384' },
        ];

        container.innerHTML = ranges
            .map(range => {
                const items = window.LISTINGS
                    .filter(l => l.price >= range.min && l.price <= range.max)
                    .sort((a, b) => (a.price || 0) - (b.price || 0));

                if (!items.length) return '';

                const rows = items.map(l => `
                    <tr>
                        <td>${createSiteBadge(l.site)}</td>
                        <td>${l.city || '—'}</td>
                        <td><strong>${formatNumber(l.price)}€</strong></td>
                        <td>${l.rooms || '—'} ch.</td>
                        <td>${l.surface || '—'} m²</td>
                        <td>${l.price_m2 ? l.price_m2 + ' €/m²' : '—'}</td>
                        <td><a href="${l.url}" target="_blank" rel="noopener noreferrer">${(l.title || 'Voir').substring(0, 45)}</a></td>
                    </tr>
                `).join('');

                return `
                    <div class="price-range-section">
                        <h5>
                            <span class="price-badge" style="background:${range.color};color:white">${range.label}</span>
                            <span class="listing-count ms-2">${items.length} annonces</span>
                        </h5>
                        <div class="table-responsive">
                            <table class="table table-sm table-hover mb-0">
                                <caption class="visually-hidden">Annonces dans la gamme ${range.label}</caption>
                                <thead>
                                    <tr>
                                        <th scope="col">Site</th>
                                        <th scope="col">Ville</th>
                                        <th scope="col">Prix</th>
                                        <th scope="col">Ch.</th>
                                        <th scope="col">m²</th>
                                        <th scope="col">€/m²</th>
                                        <th scope="col">Titre</th>
                                    </tr>
                                </thead>
                                <tbody>${rows}</tbody>
                            </table>
                        </div>
                    </div>
                `;
            })
            .filter(Boolean)
            .join('');
    } catch (err) {
        console.error('Error rendering price view:', err);
    }
}

// ==================== MAP ====================

function initMapTab() {
    const mapBtn = document.querySelector('[data-bs-target="#tab-map"]');
    if (!mapBtn) return;

    mapBtn.addEventListener('shown.bs.tab', () => {
        if (state.mapInitialized) return;
        state.mapInitialized = true;
        renderMap();
    });
}

function renderMap() {
    try {
        const withGPS = window.LISTINGS.filter(l => l.latitude && l.longitude);
        const mapContainer = document.getElementById('map');

        if (!withGPS.length) {
            mapContainer.innerHTML = '<p class="text-center text-muted py-5">Aucune annonce avec coordonnées GPS</p>';
            return;
        }

        // Check if Leaflet is available
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded');
            mapContainer.innerHTML = '<p class="text-center text-danger py-5">Erreur de chargement de la carte</p>';
            return;
        }

        const map = L.map('map').setView([CONFIG.MAP_INIT_LAT, CONFIG.MAP_INIT_LON], CONFIG.MAP_INIT_ZOOM);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(map);

        const bounds = [];

        withGPS.forEach(l => {
            const color = CONFIG.SITE_COLORS[l.site] || '#888';

            L.circleMarker([l.latitude, l.longitude], {
                radius: 7,
                fillColor: color,
                color: '#fff',
                weight: 2,
                fillOpacity: 0.85,
            })
            .addTo(map)
            .bindPopup(`
                <strong>${l.city || '—'}</strong><br>
                ${formatNumber(l.price)}€ | ${l.rooms || '?'} ch. | ${l.surface || '?'} m²<br>
                <a href="${l.url}" target="_blank" rel="noopener noreferrer">Voir l'annonce</a>
            `);

            bounds.push([l.latitude, l.longitude]);
        });

        if (bounds.length) {
            map.fitBounds(bounds, { padding: [30, 30] });
        }
    } catch (err) {
        console.error('Error rendering map:', err);
        document.getElementById('map').innerHTML = '<p class="text-center text-danger py-5">Erreur lors du chargement de la carte</p>';
    }
}

// ==================== EXPORT CSV ====================

function exportCSV() {
    try {
        const headers = ['Site', 'Ville', 'Prix', 'Chambres', 'Surface', 'Prix/m²', 'Distance', 'Titre', 'URL'];
        const rows = state.filtered.map(l => [
            l.site || '',
            l.city || '',
            l.price || '',
            l.rooms || '',
            l.surface || '',
            l.price_m2 || '',
            l.distance_km || '',
            (l.title || '').replace(/[";]/g, ' '),
            l.url || '',
        ]);

        const csv = [headers, ...rows]
            .map(r => r.map(c => `"${c}"`).join(';'))
            .join('\n');

        const bom = '\ufeff';
        const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `immolux_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } catch (err) {
        console.error('Error exporting CSV:', err);
        alert('Erreur lors de l\'export CSV');
    }
}

// ==================== WEB SHARE API ====================

function initShareButton() {
    const shareBtn = document.getElementById('shareBtn');
    if (!shareBtn) return;

    // Check if Web Share API is available
    if (navigator.share) {
        shareBtn.style.display = 'inline-block';
        shareBtn.addEventListener('click', async () => {
            try {
                const title = `ImmoLux Dashboard - ${state.filtered.length} annonces`;
                const text = `Découvrez les annonces immobilières du Luxembourg sur ImmoLux Dashboard`;
                const url = window.location.href;

                await navigator.share({ title, text, url });
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Error sharing:', err);
                }
            }
        });
    } else {
        // Fallback: copy URL to clipboard
        shareBtn.addEventListener('click', () => {
            const url = window.location.href;
            navigator.clipboard.writeText(url).then(() => {
                shareBtn.textContent = '✅ Copié!';
                setTimeout(() => {
                    shareBtn.innerHTML = '🔗 Partager';
                }, 2000);
            }).catch(() => {
                alert('Erreur lors de la copie du lien');
            });
        });
    }
}

// ==================== STATISTICS ====================

function updateStats() {
    try {
        const total = window.LISTINGS.length;
        const prices = window.LISTINGS.filter(l => l.price > 0).map(l => l.price);
        const surfaces = window.LISTINGS.filter(l => l.surface > 0).map(l => l.surface);
        const cities = typeof CityNormalizer !== 'undefined' && CityNormalizer.getUniqueCities
            ? CityNormalizer.getUniqueCities(window.LISTINGS)
            : [...new Set(window.LISTINGS
                .map(l => l.city)
                .filter(c => c && c !== 'N/A')
            )];
        const sites = [...new Set(window.LISTINGS
            .map(l => l.site)
            .filter(Boolean)
        )];

        const avgPrice = prices.length
            ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)
            : 0;
        const minPrice = prices.length ? Math.min(...prices) : 0;
        const maxPrice = prices.length ? Math.max(...prices) : 0;
        const avgSurface = surfaces.length
            ? Math.round(surfaces.reduce((a, b) => a + b, 0) / surfaces.length)
            : 0;

        // Update header
        document.getElementById('totalCount').textContent = total;
        document.getElementById('cityCount').textContent = cities.length;
        document.getElementById('siteCount').textContent = sites.length;

        // Update cards
        document.getElementById('statTotal').textContent = total;
        document.getElementById('statAvgPrice').textContent = formatNumber(avgPrice) + '€';
        document.getElementById('statMinPrice').textContent = formatNumber(minPrice) + '€';
        document.getElementById('statMaxPrice').textContent = formatNumber(maxPrice) + '€';
        document.getElementById('statAvgSurface').textContent = avgSurface + 'm²';
        document.getElementById('statCities').textContent = cities.length;
    } catch (err) {
        console.error('Error updating stats:', err);
    }
}

// ==================== BACK TO TOP ====================

function initBackToTop() {
    const backToTopBtn = document.getElementById('backToTop');
    if (!backToTopBtn) return;

    window.addEventListener('scroll', () => {
        backToTopBtn.style.display = window.scrollY > 300 ? 'block' : 'none';
    });

    backToTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ==================== DARK MODE ====================

function initDarkMode() {
    const toggle = document.getElementById('darkModeToggle');
    if (!toggle) return;

    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        toggle.setAttribute('aria-pressed', 'true');
    }

    toggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isNowDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isNowDark);
        toggle.setAttribute('aria-pressed', isNowDark);
    });
}

// ==================== SERVICE WORKER ====================

function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('../sw.js')
            .then(reg => console.log('✓ Service Worker registered:', reg.scope))
            .catch(err => console.log('✗ Service Worker registration failed:', err));
    }
}

// ==================== MAIN INITIALIZATION ====================

function init() {
    try {
        // Check if data is available
        if (!window.LISTINGS || !Array.isArray(window.LISTINGS)) {
            console.error('LISTINGS data not available');
            return;
        }

        // Normalize city names
        if (typeof CityNormalizer !== 'undefined' && CityNormalizer.normalizeListings) {
            window.LISTINGS = CityNormalizer.normalizeListings(window.LISTINGS);
            console.log('✓ City names normalized');
        }

        // Initialize
        initDarkMode();
        updateStats();
        initFilters();
        initTableSorting();

        // Restore state from URL
        restoreFilterStateFromUrl();

        // Apply initial filters
        applyFilters();

        // Render views
        renderCityView();
        renderPriceView();

        // Initialize interactive elements
        initMapTab();
        initBackToTop();
        initShareButton();

        // Filter event listeners
        ['f-city', 'f-site'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', applyFilters);
        });

        ['f-pmin', 'f-pmax', 'f-smin'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', applyFilters);
        });

        // PWA
        registerServiceWorker();

        // Update timestamp
        const updateEl = document.getElementById('lastUpdate');
        if (updateEl) {
            updateEl.textContent = `Mis à jour: ${new Date().toLocaleString('fr-FR')}`;
        }

        console.log('✓ ImmoLux Dashboard v2 initialized');
    } catch (err) {
        console.error('Critical error during initialization:', err);
    }
}

// ==================== STARTUP ====================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
