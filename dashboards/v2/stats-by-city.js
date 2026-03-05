// ==================== STATS BY CITY ====================

let TRANSPORTS = {};
let allListings = [];
let cityStats = {};
let allCities = [];

// ==================== INITIALIZATION ====================

function init() {
    try {
        if (!window.LISTINGS || !Array.isArray(window.LISTINGS)) {
            console.error('LISTINGS data not available');
            document.getElementById('listingsByCityContainer').innerHTML =
                '<div class="alert alert-danger">Erreur : données non disponibles</div>';
            return;
        }

        allListings = window.LISTINGS;

        // Load transport data
        loadTransportData();

        // Calculate stats
        calculateStats();

        // Render UI
        updateTimestamp();
        renderQuickStats();
        renderListingsByCity();

        console.log('✓ Stats by city initialized');
    } catch (err) {
        console.error('Critical error during initialization:', err);
    }
}

function loadTransportData() {
    fetch('data/city-transports.json')
        .then(r => r.json())
        .then(data => {
            TRANSPORTS = data.cities || {};
            console.log('✓ Transports loaded:', Object.keys(TRANSPORTS).length, 'cities');
        })
        .catch(err => console.log('Transport data not available:', err));
}

// ==================== STATISTICS CALCULATION ====================

function calculateStats() {
    const byCity = {};

    allListings.forEach(listing => {
        const city = listing.city || 'N/A';
        if (!byCity[city]) byCity[city] = [];
        byCity[city].push(listing);
    });

    allCities = Object.keys(byCity).sort();

    // Calculate detailed stats per city
    allCities.forEach(city => {
        const listings = byCity[city];
        const prices = listings.filter(l => l.price > 0).map(l => l.price);
        const surfaces = listings.filter(l => l.surface > 0).map(l => l.surface);
        const rooms = listings.filter(l => l.rooms > 0).map(l => l.rooms);

        const minPrice = prices.length ? Math.min(...prices) : 0;
        const maxPrice = prices.length ? Math.max(...prices) : 0;
        const avgPrice = prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0;
        const avgSurface = surfaces.length ? Math.round(surfaces.reduce((a, b) => a + b, 0) / surfaces.length) : 0;
        const avgRooms = rooms.length ? (rooms.reduce((a, b) => a + b, 0) / rooms.length).toFixed(1) : 0;

        cityStats[city] = {
            count: listings.length,
            minPrice,
            maxPrice,
            avgPrice,
            avgSurface,
            avgRooms,
            listings: listings
        };
    });
}

// ==================== QUICK STATS RENDERING ====================

function renderQuickStats() {
    if (allCities.length === 0) return;

    const totalListings = allListings.length;
    const avgPrice = Math.round(
        allListings
            .filter(l => l.price > 0)
            .reduce((sum, l) => sum + l.price, 0) / allListings.length
    );
    const avgSurface = Math.round(
        allListings
            .filter(l => l.surface > 0)
            .reduce((sum, l) => sum + l.surface, 0) / allListings.length
    );

    const statsHtml = `
        <div class="stat-card">
            <div class="stat-value">${allCities.length}</div>
            <div class="stat-label">Villes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${totalListings}</div>
            <div class="stat-label">Annonces</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${avgPrice.toLocaleString('fr-FR')}€</div>
            <div class="stat-label">Prix Moyen</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${avgSurface}m²</div>
            <div class="stat-label">Surface Moy.</div>
        </div>
    `;

    document.getElementById('quickStats').innerHTML = statsHtml;
}

// ==================== FILTERING & RENDERING ====================

function filterCities() {
    renderListingsByCity();
}

function renderListingsByCity() {
    const container = document.getElementById('listingsByCityContainer');
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const byCity = {};

    allListings.forEach(l => {
        const city = l.city || 'N/A';
        if (!byCity[city]) byCity[city] = [];
        byCity[city].push(l);
    });

    const cities = Object.keys(byCity).sort();

    // Filter cities based on search
    const filteredCities = cities.filter(city =>
        city.toLowerCase().includes(searchTerm)
    );

    // Update city count
    const totalListings = filteredCities.reduce((sum, city) => sum + byCity[city].length, 0);
    document.getElementById('cityCount').textContent =
        `📊 ${filteredCities.length} villes • ${totalListings} annonces`;

    // Render city cards
    container.innerHTML = filteredCities
        .map((city, idx) => renderCityCard(city, byCity[city], idx))
        .join('');

    // Add click handlers for collapsible cards
    document.querySelectorAll('.city-header').forEach(header => {
        header.addEventListener('click', (e) => {
            const card = header.closest('.city-card');
            card.classList.toggle('expanded');
            const content = card.querySelector('.city-content');
            content.classList.toggle('collapsed');
        });
    });
}

function renderCityCard(city, listings, idx) {
    const transport = TRANSPORTS[city] || {};
    const transportList = transport.transports || [];

    const transportIcons = transportList.length > 0
        ? transportList.slice(0, 3).map(t => getTransportIcon(t.type)).join(' ')
        : '⚠️';

    return `
        <div class="city-card" id="city-${idx}">
            <div class="city-header">
                <div class="city-name">
                    <span>📍</span>
                    <span class="city-name-text">${city}</span>
                    <span class="city-badge">${listings.length} annonces</span>
                </div>
                <div class="city-transport">
                    ${transportList.length > 0
                        ? `<span class="transport-icon">${transportIcons}</span><span>${transport.distance_km ? transport.distance_km + ' km' : ''}</span>`
                        : '<span>Transports non disponibles</span>'
                    }
                </div>
                <div style="margin-left: auto;">
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="city-content collapsed">
                ${transportList.length > 0 ? renderTransportInfo(transport, transportList) : ''}
                ${renderListingsTable(listings)}
            </div>
        </div>
    `;
}

function renderTransportInfo(transport, transportList) {
    return `
        <div class="transport-info">
            <div class="transport-header">
                <span>🚊 Moyens de transport vers Gare Centrale</span>
                ${transport.distance_km != null ? `<span class="transport-distance">📏 ${transport.distance_km} km${transport.region ? ` • ${transport.region}` : ''}</span>` : ''}
            </div>
            ${transportList.map(t => `
                <div class="transport-item">
                    <span class="transport-icon">${getTransportIcon(t.type)}</span>
                    <span class="transport-number"><strong>${t.number}</strong></span>
                    <span>— ${t.description}</span>
                    <span class="transport-time">(${t.duration_min} min)</span>
                </div>
            `).join('')}
        </div>
    `;
}

function renderListingsTable(listings) {
    return `
        <table class="listings-table">
            <thead>
                <tr>
                    <th>Titre</th>
                    <th>Prix</th>
                    <th style="text-align: center;">Chambres</th>
                    <th style="text-align: center;">Surface</th>
                    <th style="text-align: center;">Action</th>
                </tr>
            </thead>
            <tbody>
                ${listings.map(l => `
                    <tr>
                        <td><span class="listing-title" title="${l.title}">${l.title.substring(0, 35)}${l.title.length > 35 ? '...' : ''}</span></td>
                        <td><span class="listing-price">${l.price.toLocaleString('fr-FR')}€</span></td>
                        <td style="text-align: center;">${l.rooms || '—'}</td>
                        <td style="text-align: center;">${l.surface || '—'}m²</td>
                        <td style="text-align: center;">
                            <a href="${l.url}" target="_blank" class="btn btn-primary btn-view">
                                Voir
                            </a>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function getTransportIcon(type) {
    const icons = {
        'gare': '🚉',
        'train': '🚂',
        'bus': '🚌',
        'tram': '🚊',
        'pied': '🚶',
        'metro': '🚇'
    };
    return icons[type] || '🚇';
}

// ==================== UTILITIES ====================

function updateTimestamp() {
    const navUpd = document.getElementById('nav-upd');
    if (navUpd) {
        const now = new Date();
        navUpd.textContent = `Mis à jour : ${now.toLocaleString('fr-FR')}`;
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
