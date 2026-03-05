// ==================== ADVANCED MAP INITIALIZATION ====================

// Fallback for ANOMALIES if not loaded
if (typeof ANOMALIES === 'undefined') {
    window.ANOMALIES = {};
}

let map;
let markerClusterGroup;
let currentMarkers = {};
let allListings = [];
let filteredListings = [];

const ANOMALY_COLORS = {
    'GOOD_DEAL': '#28a745',
    'HIGH': '#dc3545',
    'NORMAL': '#667eea'
};

// ==================== INITIALIZATION ====================

function init() {
    try {
        if (!window.LISTINGS || !Array.isArray(window.LISTINGS)) {
            console.error('LISTINGS data not available');
            document.getElementById('listings').innerHTML = '<div class="alert alert-danger">Erreur : données non disponibles</div>';
            return;
        }

        allListings = window.LISTINGS;
        filteredListings = allListings;

        initMap();
        populateFilters();
        renderListings(filteredListings);
        addMarkersToMap(filteredListings);
        updateTimestamp();

        console.log('✓ Advanced Map initialized');
    } catch (err) {
        console.error('Critical error during initialization:', err);
        document.getElementById('listings').innerHTML = '<div class="alert alert-danger">Erreur critique</div>';
    }
}

// ==================== MAP INITIALIZATION ====================

function initMap() {
    const centerLat = 49.6116;  // Luxembourg center
    const centerLng = 6.1319;

    map = L.map('map').setView([centerLat, centerLng], 9);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
        className: document.body.classList.contains('dark-mode') ? 'leaflet-dark' : ''
    }).addTo(map);

    // Cluster group
    markerClusterGroup = L.markerClusterGroup({
        maxClusterRadius: 80,
        iconCreateFunction: createClusterIcon
    });
    map.addLayer(markerClusterGroup);
}

function createClusterIcon(cluster) {
    const count = cluster.getChildCount();
    const size = count < 10 ? 40 : count < 50 ? 50 : 60;
    return L.divIcon({
        html: `<div style="background:#667eea; color:white; width:${size}px; height:${size}px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:0.85rem;">${count}</div>`,
        iconSize: [size, size],
        className: 'cluster-icon'
    });
}

// ==================== FILTERS ====================

function populateFilters() {
    const cities = [...new Set(allListings
        .map(l => l.city)
        .filter(c => c && c.trim())
    )].sort();

    const sites = [...new Set(allListings
        .map(l => l.site)
        .filter(s => s && s.trim())
    )].sort();

    const citySelect = document.getElementById('filterCity');
    cities.forEach(city => {
        const opt = document.createElement('option');
        opt.value = city;
        opt.textContent = city;
        citySelect.appendChild(opt);
    });

    const siteSelect = document.getElementById('filterSite');
    sites.forEach(site => {
        const opt = document.createElement('option');
        opt.value = site;
        opt.textContent = site;
        siteSelect.appendChild(opt);
    });
}

function applyMapFilters() {
    const city = document.getElementById('filterCity').value;
    const site = document.getElementById('filterSite').value;

    filteredListings = allListings.filter(listing => {
        return (!city || listing.city === city) && (!site || listing.site === site);
    });

    // Refresh map and list
    markerClusterGroup.clearLayers();
    currentMarkers = {};
    renderListings(filteredListings);
    addMarkersToMap(filteredListings);
}

function resetFilters() {
    document.getElementById('filterCity').value = '';
    document.getElementById('filterSite').value = '';
    applyMapFilters();
}

// ==================== RENDERING ====================

function renderListings(listings) {
    const container = document.getElementById('listings');

    if (!listings || listings.length === 0) {
        container.innerHTML = '<div class="text-muted text-center py-4">Aucune annonce</div>';
        return;
    }

    container.innerHTML = listings.map(listing => {
        const anomaly = ANOMALIES[listing.listing_id] || 'NORMAL';
        const badgeClass = anomaly === 'GOOD_DEAL' ? 'badge-good' : anomaly === 'HIGH' ? 'badge-high' : '';
        const badgeText = anomaly === 'GOOD_DEAL' ? '✅ Bon Affaire' : anomaly === 'HIGH' ? '⚠️ Prix Haut' : '';

        return `
            <div class="listing-item" onclick="selectListing('${listing.listing_id}')" data-id="${listing.listing_id}">
                <h6 title="${listing.title}">${listing.title}</h6>
                <div class="listing-item-price">${listing.price}€</div>
                <div class="small">
                    <span class="badge bg-secondary">${listing.city || 'N/A'}</span>
                    ${anomaly !== 'NORMAL' ? `<span class="badge-anomaly ${badgeClass}">${badgeText}</span>` : ''}
                </div>
                <div class="small text-muted">
                    ${listing.surface > 0 ? `${listing.surface}m² ` : ''}
                    ${listing.rooms > 0 ? `${listing.rooms} ch ` : ''}
                    ${listing.time_ago || ''}
                </div>
            </div>
        `;
    }).join('');
}

function addMarkersToMap(listings) {
    currentMarkers = {};

    listings.forEach(listing => {
        if (!listing.latitude || !listing.longitude) return;

        const anomaly = ANOMALIES[listing.listing_id] || 'NORMAL';
        const color = ANOMALY_COLORS[anomaly];

        const marker = L.circleMarker([listing.latitude, listing.longitude], {
            radius: 8,
            fillColor: color,
            color: '#fff',
            weight: 2,
            opacity: 0.8,
            fillOpacity: 0.7
        }).bindPopup(`
            <strong>${listing.title}</strong><br/>
            <strong>${listing.price}€</strong><br/>
            ${listing.surface > 0 ? listing.surface + 'm² | ' : ''}
            ${listing.rooms > 0 ? listing.rooms + ' ch' : ''}<br/>
            <small>${listing.city || 'N/A'}</small><br/>
            <a href="${listing.url}" target="_blank" class="btn btn-sm btn-primary mt-2">Voir l'annonce</a>
        `);

        marker.on('click', () => selectListing(listing.listing_id));
        markerClusterGroup.addLayer(marker);
        currentMarkers[listing.listing_id] = marker;
    });
}

function selectListing(listingId) {
    // Highlight item in sidebar
    document.querySelectorAll('.listing-item').forEach(el => el.classList.remove('active'));
    const activeItem = document.querySelector(`[data-id="${listingId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Center map on marker
    const marker = currentMarkers[listingId];
    if (marker && map) {
        map.setView(marker.getLatLng(), 14);
        marker.openPopup();
    }
}

// ==================== UTILITIES ====================

function updateTimestamp() {
    const navUpd = document.getElementById('nav-upd');
    if (navUpd && window.lastUpdate) {
        navUpd.textContent = `Mis à jour : ${window.lastUpdate}`;
    }
}

// ==================== DARK MODE ====================

if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}

document.getElementById('darkModeToggle').addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
});

// ==================== SERVICE WORKER ====================

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('../sw.js')
        .then(reg => console.log('✓ Service Worker registered'))
        .catch(err => console.log('Service Worker registration failed:', err));
}

// ==================== STARTUP ====================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
