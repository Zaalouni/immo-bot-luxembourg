/**
 * ImmoLux Map - v2.0.0-beta
 * Interactive Map Logic
 * Date: 2026-03-05
 */

'use strict';

// ==================== CONFIGURATION ====================
const MAP_CONFIG = {
    CENTER_LAT: 49.6116,
    CENTER_LON: 6.1319,
    INIT_ZOOM: 10,
    MAX_ZOOM: 19,
    TILE_URL: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    TILE_ATTRIBUTION: '© OpenStreetMap contributors',
};

const SITE_COLORS = {
    'Remax.lu': '#e74c3c',
    'Nexvia.lu': '#3498db',
    'Immoweb.lu': '#9b59b6',
    'Athome.lu': '#2ecc71',
    'Paperjob.lu': '#f39c12',
    'Cascella.lu': '#1abc9c',
    'Immomo.lu': '#e67e22',
};

// ==================== STATE ====================
const mapState = {
    map: null,
    markerClusterGroup: null,
    allMarkers: [],
    filteredMarkers: [],
};

// ==================== INITIALIZATION ====================

function initMap() {
    try {
        // Initialize Leaflet map
        mapState.map = L.map('map').setView(
            [MAP_CONFIG.CENTER_LAT, MAP_CONFIG.CENTER_LON],
            MAP_CONFIG.INIT_ZOOM
        );

        // Add OSM tile layer
        L.tileLayer(MAP_CONFIG.TILE_URL, {
            attribution: MAP_CONFIG.TILE_ATTRIBUTION,
            maxZoom: MAP_CONFIG.MAX_ZOOM,
        }).addTo(mapState.map);

        // Initialize marker cluster group
        mapState.markerClusterGroup = L.markerClusterGroup({
            maxClusterRadius: 80,
            disableClusteringAtZoom: 17,
        }).addTo(mapState.map);

        console.log('✓ Map initialized');
    } catch (err) {
        console.error('Error initializing map:', err);
    }
}

// ==================== MARKERS ====================

function addMarkers(listings) {
    try {
        mapState.allMarkers = [];
        mapState.markerClusterGroup.clearLayers();

        const geoListings = listings.filter(l => l.latitude && l.longitude);

        geoListings.forEach(listing => {
            const color = SITE_COLORS[listing.site] || '#888';
            const marker = L.circleMarker(
                [listing.latitude, listing.longitude],
                {
                    radius: 7,
                    fillColor: color,
                    color: '#fff',
                    weight: 2,
                    fillOpacity: 0.85,
                }
            );

            // Popup content
            const popupContent = `
                <div style="min-width: 200px;">
                    <strong>${listing.city || 'Unknown'}</strong><br>
                    <small style="color: #666;">${listing.site}</small><br>
                    <br>
                    <strong>${formatPrice(listing.price)}€</strong><br>
                    ${listing.rooms ? `${listing.rooms} ch. • ` : ''}
                    ${listing.surface ? `${listing.surface} m² ` : ''}
                    ${listing.distance_km ? `• ${listing.distance_km} km` : ''}<br>
                    <br>
                    <a href="${listing.url}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; text-decoration: none;">
                        Voir l'annonce →
                    </a>
                </div>
            `;

            marker.bindPopup(popupContent);
            marker.listing = listing;

            mapState.allMarkers.push(marker);
            mapState.markerClusterGroup.addLayer(marker);
        });

        // Update stats
        updateMapStats(listings, geoListings.length);

        // Update legend
        updateLegend();

        console.log(`✓ Added ${geoListings.length} markers to map`);
    } catch (err) {
        console.error('Error adding markers:', err);
    }
}

// ==================== FORMATTING ====================

function formatPrice(price) {
    if (!price) return '—';
    return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

// ==================== FILTERS ====================

function initializeFilters() {
    try {
        const cities = [...new Set(window.LISTINGS
            .map(l => l.city)
            .filter(c => c && c !== 'N/A')
        )].sort();

        const sites = [...new Set(window.LISTINGS
            .map(l => l.site)
            .filter(Boolean)
        )].sort();

        // Populate city select
        const citySelect = document.getElementById('filter-city');
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        });

        // Populate site select
        const siteSelect = document.getElementById('filter-site');
        sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site;
            option.textContent = site;
            siteSelect.appendChild(option);
        });

        // Add event listeners
        document.getElementById('filter-city').addEventListener('change', applyFilters);
        document.getElementById('filter-site').addEventListener('change', applyFilters);
        document.getElementById('filter-price-min').addEventListener('input', applyFilters);
        document.getElementById('filter-price-max').addEventListener('input', applyFilters);

        console.log('✓ Filters initialized');
    } catch (err) {
        console.error('Error initializing filters:', err);
    }
}

function applyFilters() {
    try {
        const city = document.getElementById('filter-city').value;
        const site = document.getElementById('filter-site').value;
        const priceMin = parseInt(document.getElementById('filter-price-min').value) || 0;
        const priceMax = parseInt(document.getElementById('filter-price-max').value) || 999999;

        mapState.filteredMarkers = mapState.allMarkers.filter(marker => {
            const l = marker.listing;
            if (city && l.city !== city) return false;
            if (site && l.site !== site) return false;
            if (l.price < priceMin || l.price > priceMax) return false;
            return true;
        });

        // Update map
        mapState.markerClusterGroup.clearLayers();
        mapState.filteredMarkers.forEach(marker => {
            mapState.markerClusterGroup.addLayer(marker);
        });

        // Update count
        document.getElementById('geo-count').textContent = mapState.filteredMarkers.length;

        console.log(`✓ Applied filters: ${mapState.filteredMarkers.length} markers visible`);
    } catch (err) {
        console.error('Error applying filters:', err);
    }
}

function resetFilters() {
    try {
        document.getElementById('filter-city').value = '';
        document.getElementById('filter-site').value = '';
        document.getElementById('filter-price-min').value = '';
        document.getElementById('filter-price-max').value = '';
        applyFilters();
    } catch (err) {
        console.error('Error resetting filters:', err);
    }
}

// ==================== PANEL TOGGLE ====================

function togglePanel() {
    const panel = document.getElementById('panel');
    panel.classList.toggle('collapsed');
    const ph = panel.querySelector('.ph');
    const isCollapsed = panel.classList.contains('collapsed');
    ph.setAttribute('aria-expanded', !isCollapsed);
}

// ==================== LEGEND ====================

function updateLegend() {
    try {
        const legendDiv = document.getElementById('legend');
        const sites = [...new Set(window.LISTINGS.map(l => l.site).filter(Boolean))];

        legendDiv.innerHTML = sites.map(site => `
            <div class="legend-row">
                <span class="dot" style="background:${SITE_COLORS[site] || '#888'}"></span>
                ${site}
            </div>
        `).join('');

        // Add distance legend
        legendDiv.innerHTML += `
            <hr style="margin: 0.4rem 0; border: none; border-top: 1px solid #e2e8f0;">
            <div style="margin-top: 0.4rem; font-size: 0.7rem; color: #94a3b8;">
                <div class="legend-row"><span class="dot" style="background:#22c55e"></span>&lt; 5 km</div>
                <div class="legend-row"><span class="dot" style="background:#fbbf24"></span>5 - 10 km</div>
                <div class="legend-row"><span class="dot" style="background:#ef4444"></span>&gt; 10 km</div>
                <div class="legend-row"><span class="dot" style="background:#94a3b8"></span>Distance inconnue</div>
            </div>
        `;
    } catch (err) {
        console.error('Error updating legend:', err);
    }
}

// ==================== STATISTICS ====================

function updateMapStats(allListings, geoCount) {
    try {
        const total = allListings.length;
        const prices = allListings.filter(l => l.price > 0).map(l => l.price);
        const avgPrice = prices.length
            ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)
            : 0;

        document.getElementById('stats-total').textContent = total;
        document.getElementById('stats-avg').textContent = formatPrice(avgPrice) + '€';
        document.getElementById('geo-count').textContent = geoCount;
    } catch (err) {
        console.error('Error updating stats:', err);
    }
}

// ==================== UI UPDATES ====================

function updateTimestamp() {
    const el = document.getElementById('nav-upd');
    if (el) {
        el.textContent = `Mis à jour : ${new Date().toLocaleString('fr-FR')}`;
    }
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
            .then(reg => console.log('✓ Service Worker registered'))
            .catch(err => console.log('✗ Service Worker registration failed:', err));
    }
}

// ==================== MAIN INITIALIZATION ====================

function init() {
    try {
        if (!window.LISTINGS || !Array.isArray(window.LISTINGS)) {
            console.error('LISTINGS data not available');
            return;
        }

        initDarkMode();
        initMap();
        addMarkers(window.LISTINGS);
        initializeFilters();
        updateTimestamp();
        registerServiceWorker();

        console.log('✓ ImmoLux Map v2 initialized');
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
