/**
 * version-display.js — Affiche la version du dashboard dans toutes les pages
 * Lit VERSION_INFO depuis data/version.js (généré par dashboard_generator.py)
 */
(function () {
    'use strict';

    function showVersion() {
        if (typeof VERSION_INFO === 'undefined') return;

        const v = VERSION_INFO.version || '?';
        const builtAt = VERSION_INFO.built_at || '';
        const total = VERSION_INFO.total_listings || '';

        const label = `v${v} · ${builtAt}${total ? ' · ' + total + ' annonces' : ''}`;

        // Injecter dans lastUpdate ou nav-upd si présents
        const lastUpdate = document.getElementById('lastUpdate');
        const navUpd = document.getElementById('nav-upd');

        if (lastUpdate) {
            lastUpdate.textContent = `Mis à jour: ${builtAt}`;
            lastUpdate.title = `Dashboard ${label}`;
        }
        if (navUpd && navUpd.textContent === 'Mis à jour : —') {
            navUpd.textContent = `Mis à jour : ${builtAt}`;
        }

        // Badge version fixe en bas à gauche (toutes les pages)
        const badge = document.createElement('div');
        badge.id = 'version-badge';
        badge.textContent = `v${v}`;
        badge.title = label;
        badge.style.cssText = [
            'position:fixed', 'bottom:0.5rem', 'left:0.5rem',
            'background:rgba(102,126,234,0.85)', 'color:#fff',
            'font-size:0.7rem', 'font-weight:600', 'padding:0.2rem 0.5rem',
            'border-radius:10px', 'z-index:9999', 'cursor:default',
            'backdrop-filter:blur(4px)', 'letter-spacing:0.03em'
        ].join(';');
        badge.setAttribute('aria-label', `Version du dashboard: ${label}`);
        document.body.appendChild(badge);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showVersion);
    } else {
        showVersion();
    }
})();
